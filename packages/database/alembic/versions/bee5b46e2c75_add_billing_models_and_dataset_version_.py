"""add_billing_models_and_dataset_version_fks

Revision ID: bee5b46e2c75
Revises: 0d95e9384c25
Create Date: 2026-08-17 16:41:03.914548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bee5b46e2c75'
down_revision: Union[str, Sequence[str], None] = '0d95e9384c25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create Enums
    payment_provider = postgresql.ENUM('STRIPE', 'RAZORPAY', 'MANUAL', name='payment_provider', create_type=False)
    payment_provider.create(op.get_bind(), checkfirst=True)

    payment_status = postgresql.ENUM('CREATED', 'PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED', 'DISPUTED', name='payment_status', create_type=False)
    payment_status.create(op.get_bind(), checkfirst=True)

    subscription_status = postgresql.ENUM('ACTIVE', 'PAST_DUE', 'CANCELED', 'UNPAID', 'INCOMPLETE', 'TRIALING', name='subscription_status', create_type=False)
    subscription_status.create(op.get_bind(), checkfirst=True)

    invoice_status = postgresql.ENUM('DRAFT', 'OPEN', 'PAID', 'VOID', 'UNCOLLECTIBLE', name='invoice_status', create_type=False)
    invoice_status.create(op.get_bind(), checkfirst=True)

    billing_cycle = postgresql.ENUM('ONE_TIME', 'MONTHLY', 'YEARLY', name='billing_cycle', create_type=False)
    billing_cycle.create(op.get_bind(), checkfirst=True)

    credit_transaction_type = postgresql.ENUM('GRANT', 'PURCHASE', 'DEDUCTION', 'REFUND', name='credit_transaction_type', create_type=False)
    credit_transaction_type.create(op.get_bind(), checkfirst=True)

    # 2. Add columns to executions and test_cases
    op.add_column('executions', sa.Column('dataset_version_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_executions_dataset_version_id'), 'executions', ['dataset_version_id'], unique=False)
    op.create_foreign_key(op.f('fk_executions_dataset_version_id_dataset_versions'), 'executions', 'dataset_versions', ['dataset_version_id'], ['id'], ondelete='CASCADE')

    op.add_column('test_cases', sa.Column('dataset_version_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_test_cases_dataset_version_id'), 'test_cases', ['dataset_version_id'], unique=False)
    op.create_foreign_key(op.f('fk_test_cases_dataset_version_id_dataset_versions'), 'test_cases', 'dataset_versions', ['dataset_version_id'], ['id'], ondelete='CASCADE')

    # 3. Create Root Tables
    op.create_table(
        'products',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_products_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_products_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_products'))
    )

    op.create_table(
        'features',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_features_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_features_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_features')),
        sa.UniqueConstraint('name', name=op.f('uq_features_name'))
    )

    op.create_table(
        'credit_accounts',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('balance', sa.Numeric(precision=15, scale=2), nullable=False, default=0),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_credit_accounts_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_credit_accounts_org_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_credit_accounts_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_credit_accounts')),
        sa.UniqueConstraint('org_id', name=op.f('uq_credit_accounts_org_id'))
    )

    op.create_table(
        'usage_records',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('metric', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_usage_records_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_usage_records_org_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_usage_records_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_usage_records'))
    )
    op.create_index(op.f('ix_usage_records_org_id'), 'usage_records', ['org_id'], unique=False)

    op.create_table(
        'webhook_events',
        sa.Column('provider', payment_provider, nullable=False),
        sa.Column('provider_event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_webhook_events_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_webhook_events_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_webhook_events')),
        sa.UniqueConstraint('provider', 'provider_event_id', name=op.f('uq_webhook_event_provider_event_id'))
    )

    # 4. Child Level 1
    op.create_table(
        'prices',
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('billing_cycle', billing_cycle, nullable=False),
        sa.Column('provider_price_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_prices_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_prices_product_id_products'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_prices_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_prices'))
    )
    op.create_index(op.f('ix_prices_product_id'), 'prices', ['product_id'], unique=False)
    op.create_index(op.f('ix_prices_provider_price_id'), 'prices', ['provider_price_id'], unique=False)

    op.create_table(
        'credit_transactions',
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('transaction_type', credit_transaction_type, nullable=False),
        sa.Column('reference_type', sa.String(length=255), nullable=True),
        sa.Column('reference_id', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], name=op.f('fk_credit_transactions_account_id_credit_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_credit_transactions_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_credit_transactions_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_credit_transactions'))
    )
    op.create_index(op.f('ix_credit_transactions_account_id'), 'credit_transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_reference_id'), 'credit_transactions', ['reference_id'], unique=False)

    # 5. Child Level 2
    op.create_table(
        'price_features',
        sa.Column('price_id', sa.UUID(), nullable=False),
        sa.Column('feature_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_price_features_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['feature_id'], ['features.id'], name=op.f('fk_price_features_feature_id_features'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['price_id'], ['prices.id'], name=op.f('fk_price_features_price_id_prices'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_price_features_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_price_features'))
    )
    op.create_index(op.f('ix_price_features_feature_id'), 'price_features', ['feature_id'], unique=False)
    op.create_index(op.f('ix_price_features_price_id'), 'price_features', ['price_id'], unique=False)

    op.create_table(
        'subscriptions',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('price_id', sa.UUID(), nullable=False),
        sa.Column('status', subscription_status, nullable=False),
        sa.Column('provider', payment_provider, nullable=True),
        sa.Column('provider_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_subscriptions_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_subscriptions_org_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['price_id'], ['prices.id'], name=op.f('fk_subscriptions_price_id_prices'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_subscriptions_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_subscriptions'))
    )
    op.create_index(op.f('ix_subscriptions_org_id'), 'subscriptions', ['org_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_price_id'), 'subscriptions', ['price_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_provider_subscription_id'), 'subscriptions', ['provider_subscription_id'], unique=False)

    # 6. Child Level 3
    op.create_table(
        'invoices',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('subscription_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', invoice_status, nullable=False),
        sa.Column('provider', payment_provider, nullable=True),
        sa.Column('provider_invoice_id', sa.String(length=255), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('tax_region', sa.String(length=50), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_invoices_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_invoices_org_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], name=op.f('fk_invoices_subscription_id_subscriptions'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_invoices_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_invoices'))
    )
    op.create_index(op.f('ix_invoices_org_id'), 'invoices', ['org_id'], unique=False)
    op.create_index(op.f('ix_invoices_provider_invoice_id'), 'invoices', ['provider_invoice_id'], unique=False)
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)

    # 7. Child Level 4
    op.create_table(
        'payments',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', payment_status, nullable=False),
        sa.Column('provider', payment_provider, nullable=False),
        sa.Column('provider_payment_id', sa.String(length=255), nullable=True),
        sa.Column('provider_order_id', sa.String(length=255), nullable=True),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_payments_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name=op.f('fk_payments_invoice_id_invoices'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name=op.f('fk_payments_org_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_payments_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_payments')),
        sa.UniqueConstraint('idempotency_key', name=op.f('uq_payments_idempotency_key'))
    )
    op.create_index(op.f('ix_payments_invoice_id'), 'payments', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_org_id'), 'payments', ['org_id'], unique=False)
    op.create_index(op.f('ix_payments_provider_customer_id'), 'payments', ['provider_customer_id'], unique=False)
    op.create_index(op.f('ix_payments_provider_order_id'), 'payments', ['provider_order_id'], unique=False)
    op.create_index(op.f('ix_payments_provider_payment_id'), 'payments', ['provider_payment_id'], unique=False)

    # 8. Child Level 5
    op.create_table(
        'refunds',
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', payment_status, nullable=False),
        sa.Column('provider_refund_id', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_refunds_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name=op.f('fk_refunds_payment_id_payments'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_refunds_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refunds'))
    )
    op.create_index(op.f('ix_refunds_payment_id'), 'refunds', ['payment_id'], unique=False)
    op.create_index(op.f('ix_refunds_provider_refund_id'), 'refunds', ['provider_refund_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop Tables
    op.drop_table('refunds')
    op.drop_table('payments')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    op.drop_table('price_features')
    op.drop_table('prices')
    op.drop_table('webhook_events')
    op.drop_table('usage_records')
    op.drop_table('credit_transactions')
    op.drop_table('credit_accounts')
    op.drop_table('features')
    op.drop_table('products')

    # 2. Remove columns from test_cases and executions
    op.drop_constraint(op.f('fk_test_cases_dataset_version_id_dataset_versions'), 'test_cases', type_='foreignkey')
    op.drop_index(op.f('ix_test_cases_dataset_version_id'), table_name='test_cases')
    op.drop_column('test_cases', 'dataset_version_id')

    op.drop_constraint(op.f('fk_executions_dataset_version_id_dataset_versions'), 'executions', type_='foreignkey')
    op.drop_index(op.f('ix_executions_dataset_version_id'), table_name='executions')
    op.drop_column('executions', 'dataset_version_id')

    # 3. Drop Enums
    op.execute("DROP TYPE IF EXISTS credit_transaction_type")
    op.execute("DROP TYPE IF EXISTS billing_cycle")
    op.execute("DROP TYPE IF EXISTS invoice_status")
    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS payment_provider")
