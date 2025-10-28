"""Add Dashboard functionality tables

Revision ID: dashboard_tables_001
Revises: 
Create Date: 2025-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dashboard_tables_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add all Dashboard functionality tables."""
    
    # Purchase Details table
    op.create_table(
        'purchase_details',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('purchase_id', sa.String(255), sa.ForeignKey('purchases.id'), nullable=False),
        sa.Column('item_details', sa.JSON, nullable=False, default={}),
        sa.Column('download_links', sa.JSON, default=[]),
        sa.Column('download_count', sa.Integer, default=0),
        sa.Column('max_downloads', sa.Integer, default=5),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Support Tickets table
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('purchase_id', sa.String(255), sa.ForeignKey('purchases.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('issue_type', sa.String(100), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), default='open'),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('assigned_to', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
    )
    
    # Design Analytics table
    op.create_table(
        'design_analytics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('design_id', sa.String(255), sa.ForeignKey('design_assets.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.func.current_date()),
        sa.Column('views', sa.Integer, default=0),
        sa.Column('unique_viewers', sa.Integer, default=0),
        sa.Column('likes', sa.Integer, default=0),
        sa.Column('downloads', sa.Integer, default=0),
        sa.Column('revenue', sa.DECIMAL(10, 2), default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('design_id', 'date', name='unique_design_date'),
    )
    
    # User Analytics table
    op.create_table(
        'user_analytics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.func.current_date()),
        sa.Column('total_views', sa.Integer, default=0),
        sa.Column('total_sales', sa.Integer, default=0),
        sa.Column('total_revenue', sa.DECIMAL(10, 2), default=0),
        sa.Column('new_customers', sa.Integer, default=0),
        sa.Column('returning_customers', sa.Integer, default=0),
        sa.Column('analytics_data', sa.Text, default='{}'),  # JSON as text for SQLite compatibility
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )
    
    # Payment Methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('method_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('account_info', sa.Text, nullable=False),  # Encrypted in production
        sa.Column('masked_info', sa.String(255), nullable=True),
        sa.Column('is_primary', sa.Boolean, default=False),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('verification_data', sa.Text, default='{}'),  # JSON as text
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_used', sa.DateTime, nullable=True),
    )
    
    # Payout Settings table
    op.create_table(
        'payout_settings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('auto_payout_enabled', sa.Boolean, default=False),
        sa.Column('payout_threshold', sa.String(10), default='100.00'),
        sa.Column('payout_schedule', sa.String(20), default='monthly'),
        sa.Column('primary_payment_method_id', sa.String(36), sa.ForeignKey('payment_methods.id'), nullable=True),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('tax_info', sa.Text, default='{}'),  # JSON as text
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Promotion Campaigns table
    op.create_table(
        'promotion_campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('design_id', sa.String(255), sa.ForeignKey('design_assets.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('campaign_name', sa.String(255), nullable=False),
        sa.Column('campaign_type', sa.String(100), nullable=False),
        sa.Column('duration_days', sa.Integer, nullable=False),
        sa.Column('budget', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metrics', sa.Text, default='{}'),  # JSON as text
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
    )
    
    # Create indexes for better performance
    op.create_index('idx_purchase_details_purchase_id', 'purchase_details', ['purchase_id'])
    op.create_index('idx_support_tickets_user_id', 'support_tickets', ['user_id'])
    op.create_index('idx_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('idx_design_analytics_design_id', 'design_analytics', ['design_id'])
    op.create_index('idx_design_analytics_date', 'design_analytics', ['date'])
    op.create_index('idx_user_analytics_user_id', 'user_analytics', ['user_id'])
    op.create_index('idx_user_analytics_date', 'user_analytics', ['date'])
    op.create_index('idx_payment_methods_user_id', 'payment_methods', ['user_id'])
    op.create_index('idx_payment_methods_is_primary', 'payment_methods', ['is_primary'])
    op.create_index('idx_promotion_campaigns_design_id', 'promotion_campaigns', ['design_id'])
    op.create_index('idx_promotion_campaigns_user_id', 'promotion_campaigns', ['user_id'])
    op.create_index('idx_promotion_campaigns_status', 'promotion_campaigns', ['status'])
    op.create_index('idx_promotion_campaigns_expires_at', 'promotion_campaigns', ['expires_at'])


def downgrade() -> None:
    """Remove all Dashboard functionality tables."""
    
    # Drop indexes first
    op.drop_index('idx_promotion_campaigns_expires_at')
    op.drop_index('idx_promotion_campaigns_status')
    op.drop_index('idx_promotion_campaigns_user_id')
    op.drop_index('idx_promotion_campaigns_design_id')
    op.drop_index('idx_payment_methods_is_primary')
    op.drop_index('idx_payment_methods_user_id')
    op.drop_index('idx_user_analytics_date')
    op.drop_index('idx_user_analytics_user_id')
    op.drop_index('idx_design_analytics_date')
    op.drop_index('idx_design_analytics_design_id')
    op.drop_index('idx_support_tickets_status')
    op.drop_index('idx_support_tickets_user_id')
    op.drop_index('idx_purchase_details_purchase_id')
    
    # Drop tables
    op.drop_table('promotion_campaigns')
    op.drop_table('payout_settings')
    op.drop_table('payment_methods')
    op.drop_table('user_analytics')
    op.drop_table('design_analytics')
    op.drop_table('support_tickets')
    op.drop_table('purchase_details')