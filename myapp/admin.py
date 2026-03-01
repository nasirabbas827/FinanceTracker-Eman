from django.contrib import admin
from .models import CustomerUser, Expense, Income

# ==========================
# Inline for Expenses in CustomerUser
# ==========================
class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 1
    fields = ('date', 'amount', 'category', 'description', 'created_at')
    readonly_fields = ('created_at',)

# ==========================
# Inline for Incomes in CustomerUser
# ==========================
class IncomeInline(admin.TabularInline):
    model = Income
    extra = 1
    fields = ('date', 'amount', 'source', 'description', 'created_at')
    readonly_fields = ('created_at',)

# ==========================
# CustomerUser Admin
# ==========================
@admin.register(CustomerUser)
class CustomerUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'status', 'last_login', 'created_at')
    list_filter = ('status', 'gender', 'country')
    search_fields = ('username', 'email', 'full_name', 'phone')
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    inlines = [ExpenseInline, IncomeInline]

# ==========================
# Expense Admin
# ==========================
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'amount', 'category', 'description', 'created_at')
    list_filter = ('category', 'date')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)

# ==========================
# Income Admin
# ==========================
@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'amount', 'source', 'description', 'created_at')
    list_filter = ('source', 'date')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)