from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, transactions, expenses, categories, budgets, audit, reports

api_router = APIRouter()

# Register presentation routing layers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["Expenses (Legacy)"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["Budgets"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
