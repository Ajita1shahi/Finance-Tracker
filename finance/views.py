
from django.shortcuts import render, HttpResponse, redirect
from django.views import View
from finance.forms import RegisterForm, TransactionForm, GoalForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Transaction, Goal
from django.db.models import Sum
from django.utils import timezone
from .admin import TransactionResource


class RegisterView(View):
    def get(self, request, *_args, **_kwargs):
        form = RegisterForm()
        return render(request, 'finance/register.html', {'form': form})

    def post(self, request, *_args, **_kwargs):
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')

        return render(request, 'finance/register.html', {'form': form})


class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *_args, **_kwargs):
        transactions = Transaction.objects.filter(user=request.user)
        goals = Goal.objects.filter(user=request.user)

        # Calculate total income
        total_income = (
            transactions.filter(
                transaction_type='income'
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        )

        # Calculate total expenses
        total_expense = (
            transactions.filter(
                transaction_type='expense'
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        )

        # Calculate net savings
        net_savings = total_income - total_expense
        remaining_savings = max(net_savings, 0)

        # Calculate this month's income and expenses
        today = timezone.localdate()

        monthly_transactions = transactions.filter(
            date__year=today.year,
            date__month=today.month
        )

        monthly_income = (
            monthly_transactions.filter(
                transaction_type='income'
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        )

        monthly_expense = (
            monthly_transactions.filter(
                transaction_type='expense'
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        )

        monthly_savings = monthly_income - monthly_expense

        # Calculate progress for each financial goal
        goal_progress = []

        for goal in goals:
            if goal.target_amount <= 0:
                progress = 0

            elif remaining_savings >= goal.target_amount:
                progress = 100
                remaining_savings -= goal.target_amount

            elif remaining_savings > 0:
                progress = (
                    remaining_savings / goal.target_amount
                ) * 100
                remaining_savings = 0

            else:
                progress = 0

            goal_progress.append({
                'goal': goal,
                'progress': progress,
            })

        # Data passed to the dashboard template
        context = {
            'transactions': transactions,
            'goals': goals,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_savings': net_savings,
            'goal_progress': goal_progress,

            # Monthly summary
            'monthly_income': monthly_income,
            'monthly_expense': monthly_expense,
            'monthly_savings': monthly_savings,
            'current_month': today.strftime('%B %Y'),
        }

        return render(request, 'finance/dashboard.html', context)


class TransactionCreateView(LoginRequiredMixin, View):
    def get(self, request, *_args, **_kwargs):
        form = TransactionForm()
        return render(
            request,
            'finance/transaction_form.html',
            {'form': form}
        )

    def post(self, request, *_args, **_kwargs):
        form = TransactionForm(request.POST)

        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('dashboard')

        return render(
            request,
            'finance/transaction_form.html',
            {'form': form}
        )


class TransactionListView(LoginRequiredMixin, View):
    def get(self, request, *_args, **_kwargs):
        transactions = Transaction.objects.filter(user=request.user)

        return render(
            request,
            'finance/transaction_list.html',
            {'transactions': transactions}
        )


class GoalCreateView(LoginRequiredMixin, View):
    def get(self, request, *_args, **_kwargs):
        form = GoalForm()
        return render(
            request,
            'finance/goal_form.html',
            {'form': form}
        )

    def post(self, request, *_args, **_kwargs):
        form = GoalForm(request.POST)

        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('dashboard')

        return render(
            request,
            'finance/goal_form.html',
            {'form': form}
        )


def export_transactions(request):
    user_transactions = Transaction.objects.filter(user=request.user)

    transaction_resource = TransactionResource()
    dataset = transaction_resource.export(
        queryset=user_transactions
    )

    excel_data = dataset.export('xlsx')

    # Create the HTTP response for the Excel file
    response = HttpResponse(
        excel_data,
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    response['Content-Disposition'] = (
        'attachment; filename="transactions.xlsx"'
    )

    return response
