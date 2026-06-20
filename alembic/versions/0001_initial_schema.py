"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-20 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('role', sa.String(length=20), server_default="'user'", nullable=False),
        sa.Column('preferred_currency', sa.String(length=3), server_default="'USD'", nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'user_id', name='uq_categories_name_user_id')
    )
    op.create_index(op.f('ix_categories_user_id'), 'categories', ['user_id'], unique=False)

    # 3. Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default="'USD'", nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(length=20), server_default="'cash'", nullable=False),
        sa.Column('receipt_url', sa.String(length=500), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("transaction_type IN ('expense', 'income', 'transfer')", name='ck_transaction_type'),
        sa.CheckConstraint('amount > 0', name='ck_transaction_amount_positive'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_category_id'), 'transactions', ['category_id'], unique=False)
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_index('ix_txn_user_date', 'transactions', ['user_id', 'transaction_date'], unique=False)
    op.create_index('ix_txn_user_type', 'transactions', ['user_id', 'transaction_type'], unique=False)
    op.create_index('ix_txn_active', 'transactions', ['user_id', 'transaction_date'], unique=False, postgresql_where='deleted_at IS NULL')
    op.create_index('ix_txn_tags', 'transactions', ['tags'], unique=False, postgresql_using='gin')

    # 4. Create expenses VIEW for backward compatibility
    op.execute("""
        CREATE VIEW expenses AS
        SELECT
            id, user_id, category_id, amount, currency, description,
            transaction_date AS expense_date, payment_method, receipt_url,
            is_recurring, tags, deleted_at, created_at, updated_at
        FROM transactions
        WHERE transaction_type = 'expense';
    """)

    # 5. Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('limit_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('alert_threshold', sa.Numeric(precision=3, scale=2), server_default='0.80', nullable=False),
        sa.Column('alert_sent', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('limit_amount > 0', name='ck_budget_limit_positive'),
        sa.CheckConstraint('month >= 1 AND month <= 12', name='ck_budget_month_range'),
        sa.CheckConstraint('year >= 2020', name='ck_budget_year_range'),
        sa.CheckConstraint('alert_threshold > 0 AND alert_threshold <= 1.0', name='ck_budget_threshold_range'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category_id', 'month', 'year', name='uq_budgets_user_cat_period')
    )

    # 6. Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )

    # 7. Create partitioned audit_logs table using raw SQL
    op.execute("""
        CREATE TABLE audit_logs (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(30) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID,
            old_data JSONB,
            new_data JSONB,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            request_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);
    """)
    
    # Create indexes on partitioned table
    op.execute("CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);")
    op.execute("CREATE INDEX ix_audit_logs_action ON audit_logs (action);")
    op.execute("CREATE INDEX ix_audit_logs_entity_type ON audit_logs (entity_type);")
    op.execute("CREATE INDEX ix_audit_logs_request_id ON audit_logs (request_id);")
    op.execute("CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at DESC);")
    
    # Create default partition to catch any insertions
    op.execute("CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;")


def downgrade() -> None:
    # Drop in reverse order
    op.execute("DROP TABLE IF EXISTS audit_logs_default;")
    op.execute("DROP TABLE IF EXISTS audit_logs;")
    op.drop_table('refresh_tokens')
    op.drop_table('budgets')
    op.execute("DROP VIEW IF EXISTS expenses;")
    op.drop_table('transactions')
    op.drop_table('categories')
    op.drop_table('users')
