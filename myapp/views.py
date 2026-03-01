from datetime import datetime

import json
import csv

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db.models import Sum
from django.db.models.functions import TruncMonth, ExtractMonth
from django.http import HttpResponse

from .models import CustomerUser, Expense, Income
from .forms import RegisterForm, LoginForm, EditProfileForm, ExpenseForm, IncomeForm


# ────────────────────────────────────────────────
#   HELPER FUNCTIONS
# ────────────────────────────────────────────────

def get_logged_in_user(request):
    """
    Retrieve the currently logged-in user from session.
    Returns None if no valid user is found in session.
    """
    if 'user_id' not in request.session:
        return None
    
    try:
        return CustomerUser.objects.get(user_id=request.session['user_id'])
    except CustomerUser.DoesNotExist:
        return None


# ────────────────────────────────────────────────
#   PUBLIC / LANDING PAGES
# ────────────────────────────────────────────────

def index(request):
    """Render the main landing / home page (no login required)."""
    return render(request, 'index.html')


# ────────────────────────────────────────────────
#   AUTHENTICATION VIEWS
# ────────────────────────────────────────────────

def register_view(request):
    """
    Handle user registration.
    Creates a new CustomerUser record using RegisterForm.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. You can now log in.")
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """
    Custom session-based login (not using Django's built-in auth).
    Validates username + password manually and sets session variables.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                user = CustomerUser.objects.get(username=username)

                if user.status != 'active':
                    messages.error(request, "Your account is not active. Please contact support.")
                    return render(request, 'login.html', {'form': form})

                if check_password(password, user.password):
                    request.session['user_id'] = user.user_id
                    request.session['username'] = user.username
                    messages.success(request, f"Welcome back, {user.username}!")
                    return redirect('dashboard')
                else:
                    messages.error(request, "Incorrect password.")

            except CustomerUser.DoesNotExist:
                messages.error(request, "No account found with that username.")

    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Clear session data and log the user out."""
    request.session.flush()
    messages.success(request, "You have been successfully logged out.")
    return redirect('index')


# ────────────────────────────────────────────────
#   PROFILE MANAGEMENT
# ────────────────────────────────────────────────

def edit_profile(request):
    """
    Allow logged-in user to update their profile information.
    Supports file uploads (e.g. avatar) if the form includes them.
    """
    user = get_logged_in_user(request)
    if not user:
        messages.error(request, "Please log in to edit your profile.")
        return redirect('login')

    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('dashboard')
    else:
        form = EditProfileForm(instance=user)

    return render(request, 'edit_profile.html', {
        'form': form,
        'user': user,
    })


# ────────────────────────────────────────────────
#   DASHBOARD – MAIN OVERVIEW + PREDICTION
# ────────────────────────────────────────────────

def dashboard_view(request):
    """
    Main user dashboard showing:
      - Total income, expenses & balance
      - Monthly expense trend
      - Category-wise expense breakdown
      - Simple next-month expense prediction (linear regression)
    """
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    # ── Basic financial summary ────────────────────────
    total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    total_expense = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    balance = total_income - total_expense

    # ── Monthly expense trend for chart ────────────────
    monthly_expenses = (
        Expense.objects
        .filter(user=user)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    monthly_labels = [item['month'].strftime('%b %Y') for item in monthly_expenses]
    monthly_totals = [float(item['total']) for item in monthly_expenses]

    # ── Category distribution ──────────────────────────
    category_expenses = (
        Expense.objects
        .filter(user=user)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    category_labels = [item['category'] for item in category_expenses]
    category_totals = [float(item['total']) for item in category_expenses]

    # ── Simple next-month expense prediction ───────────
    predicted_expense = 0.0
    if len(monthly_expenses) >= 2:  # need at least 2 points for meaningful regression
        df = pd.DataFrame(monthly_expenses)
        df['month_idx'] = np.arange(len(df))
        
        X = df[['month_idx']]
        y = df['total']

        model = LinearRegression()
        model.fit(X, y)

        next_idx = len(df)
        predicted_expense = model.predict([[next_idx]])[0]
        predicted_expense = round(max(0, predicted_expense), 2)  # no negative prediction

    context = {
        'user': user,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_totals': json.dumps(monthly_totals),
        'category_labels': json.dumps(category_labels),
        'category_totals': json.dumps(category_totals),
        'total_income': round(float(total_income), 2),
        'total_expense': round(float(total_expense), 2),
        'balance': round(float(balance), 2),
        'predicted_expense': predicted_expense,
    }

    return render(request, 'dashboard.html', context)


# ────────────────────────────────────────────────
#   EXPENSES – CRUD + LIST + EXPORT
# ────────────────────────────────────────────────

def add_expense(request):
    """Create a new expense entry for the logged-in user."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = user
            expense.save()
            messages.success(request, "Expense added successfully.")
            return redirect('expense_list')
    else:
        form = ExpenseForm()

    return render(request, 'expenses/add_expense.html', {'form': form})


def expense_list(request):
    """
    List all expenses with filtering support.
    Shows monthly summary and basic average for overspending hint.
    """
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    expenses = Expense.objects.filter(user=user)

    # Apply filters from GET parameters
    if category := request.GET.get('category'):
        expenses = expenses.filter(category=category)
    if start_date := request.GET.get('start_date'):
        expenses = expenses.filter(date__gte=start_date)
    if end_date := request.GET.get('end_date'):
        expenses = expenses.filter(date__lte=end_date)
    if min_amount := request.GET.get('min_amount'):
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount := request.GET.get('max_amount'):
        expenses = expenses.filter(amount__lte=max_amount)

    # Monthly summary for chart
    monthly_data = (
        expenses
        .annotate(month=ExtractMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    months = [item['month'] for item in monthly_data]
    totals = [float(item['total']) for item in monthly_data]

    avg_monthly = sum(totals) / len(totals) if totals else 0

    context = {
        'expenses': expenses,
        'months': json.dumps(months),
        'totals': json.dumps(totals),
        'average': round(avg_monthly, 2),
    }

    return render(request, 'expenses/expense_list.html', context)


def edit_expense(request, pk):
    """Update an existing expense."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    expense = get_object_or_404(Expense, pk=pk, user=user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/edit_expense.html', {'form': form})


def delete_expense(request, pk):
    """Delete an expense entry."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    expense = get_object_or_404(Expense, pk=pk, user=user)
    expense.delete()
    messages.success(request, "Expense deleted successfully.")
    return redirect('expense_list')


def export_expense_csv(request):
    """Download all user's expenses as CSV."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_expenses.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Amount', 'Category', 'Description'])

    for exp in Expense.objects.filter(user=user).order_by('date'):
        writer.writerow([exp.date, exp.amount, exp.category, exp.description or ''])

    return response


# ────────────────────────────────────────────────
#   INCOMES – CRUD + LIST + EXPORT
# ────────────────────────────────────────────────

def add_income(request):
    """Create a new income entry."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = user
            income.save()
            messages.success(request, "Income recorded successfully.")
            return redirect('income_list')
    else:
        form = IncomeForm()

    return render(request, 'incomes/add_income.html', {'form': form})


def income_list(request):
    """List incomes with filtering and monthly summary chart."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    incomes = Income.objects.filter(user=user)

    # Filters
    if source := request.GET.get('source'):
        incomes = incomes.filter(source=source)
    if start_date := request.GET.get('start_date'):
        incomes = incomes.filter(date__gte=start_date)
    if end_date := request.GET.get('end_date'):
        incomes = incomes.filter(date__lte=end_date)
    if min_amount := request.GET.get('min_amount'):
        incomes = incomes.filter(amount__gte=min_amount)
    if max_amount := request.GET.get('max_amount'):
        incomes = incomes.filter(amount__lte=max_amount)

    # Monthly summary
    monthly_data = (
        incomes
        .annotate(month=ExtractMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    months = [item['month'] for item in monthly_data]
    totals = [float(item['total']) for item in monthly_data]

    context = {
        'incomes': incomes,
        'months': json.dumps(months),
        'totals': json.dumps(totals),
    }

    return render(request, 'incomes/income_list.html', context)


def edit_income(request, pk):
    """Modify an existing income record."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    income = get_object_or_404(Income, pk=pk, user=user)

    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, "Income updated.")
            return redirect('income_list')
    else:
        form = IncomeForm(instance=income)

    return render(request, 'incomes/edit_income.html', {'form': form})


def delete_income(request, pk):
    """Remove an income entry."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    income = get_object_or_404(Income, pk=pk, user=user)
    income.delete()
    messages.success(request, "Income entry deleted.")
    return redirect('income_list')


def export_income_csv(request):
    """Export all incomes to CSV file."""
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_incomes.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Amount', 'Source', 'Description'])

    for inc in Income.objects.filter(user=user).order_by('date'):
        writer.writerow([inc.date, inc.amount, inc.source, inc.description or ''])

    return response