"""Initial migration

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('salt', sa.String(length=255), nullable=False),
        sa.Column('encryption_key', sa.Text(), nullable=True),
        sa.Column('totp_secret', sa.String(length=32), nullable=True),
        sa.Column('backup_codes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('oauth_provider', sa.String(length=50), nullable=True),
        sa.Column('oauth_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('preferences', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_oauth', 'users', ['oauth_provider', 'oauth_id'], unique=False)
    op.create_index('idx_users_active', 'users', ['is_active'], unique=False)
    op.create_index('idx_users_created', 'users', ['created_at'], unique=False)

    # Create groups table
    op.create_table('groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['parent_group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_groups_user_id', 'groups', ['user_id'], unique=False)
    op.create_index('idx_groups_parent_id', 'groups', ['parent_group_id'], unique=False)
    op.create_index('idx_groups_name', 'groups', ['name'], unique=False)
    op.create_index('idx_groups_active', 'groups', ['is_active'], unique=False)
    op.create_index('idx_groups_sort', 'groups', ['sort_order'], unique=False)
    op.create_index('idx_groups_created', 'groups', ['created_at'], unique=False)

    # Create hosts table
    op.create_table('hosts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=True),
        sa.Column('private_key_encrypted', sa.Text(), nullable=True),
        sa.Column('private_key_passphrase_encrypted', sa.Text(), nullable=True),
        sa.Column('connection_type', sa.String(length=20), nullable=False),
        sa.Column('jump_host_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auth_method', sa.String(length=20), nullable=False),
        sa.Column('use_agent', sa.Boolean(), nullable=False),
        sa.Column('agent_forwarding', sa.Boolean(), nullable=False),
        sa.Column('term_type', sa.String(length=50), nullable=False),
        sa.Column('terminal_columns', sa.Integer(), nullable=False),
        sa.Column('terminal_rows', sa.Integer(), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('is_favorite', sa.Boolean(), nullable=False),
        sa.Column('connection_timeout', sa.Integer(), nullable=False),
        sa.Column('keep_alive', sa.Boolean(), nullable=False),
        sa.Column('compression', sa.Boolean(), nullable=False),
        sa.Column('port_forwardings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('ssh_options', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('connection_status', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['host_id'], ['hosts.id'], ),
        sa.ForeignKeyConstraint(['jump_host_id'], ['hosts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_hosts_user_id', 'hosts', ['user_id'], unique=False)
    op.create_index('idx_hosts_group_id', 'hosts', ['group_id'], unique=False)
    op.create_index('idx_hosts_name', 'hosts', ['name'], unique=False)
    op.create_index('idx_hosts_hostname', 'hosts', ['hostname'], unique=False)
    op.create_index('idx_hosts_tags', 'hosts', ['tags'], unique=False, postgresql_using='gin')
    op.create_index('idx_hosts_favorite', 'hosts', ['is_favorite'], unique=False)
    op.create_index('idx_hosts_active', 'hosts', ['is_active'], unique=False)
    op.create_index('idx_hosts_created', 'hosts', ['created_at'], unique=False)
    op.create_index('idx_hosts_last_connected', 'hosts', ['last_connected_at'], unique=False)

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('host_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('websocket_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_shared', sa.Boolean(), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('shared_users', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('terminal_columns', sa.Integer(), nullable=False),
        sa.Column('terminal_rows', sa.Integer(), nullable=False),
        sa.Column('term_type', sa.String(length=50), nullable=False),
        sa.Column('ssh_session_id', sa.String(length=255), nullable=True),
        sa.Column('connection_info', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('bytes_sent', sa.Integer(), nullable=False),
        sa.Column('bytes_received', sa.Integer(), nullable=False),
        sa.Column('commands_executed', sa.Integer(), nullable=False),
        sa.Column('client_info', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_recording', sa.Boolean(), nullable=False),
        sa.Column('recording_path', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['host_id'], ['hosts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'], unique=False)
    op.create_index('idx_sessions_host_id', 'sessions', ['host_id'], unique=False)
    op.create_index('idx_sessions_token', 'sessions', ['session_token'], unique=False)
    op.create_index('idx_sessions_websocket', 'sessions', ['websocket_id'], unique=False)
    op.create_index('idx_sessions_active', 'sessions', ['is_active'], unique=False)
    op.create_index('idx_sessions_shared', 'sessions', ['is_shared'], unique=False)
    op.create_index('idx_sessions_started', 'sessions', ['started_at'], unique=False)
    op.create_index('idx_sessions_last_activity', 'sessions', ['last_activity'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('authentication_method', sa.String(length=50), nullable=True),
        sa.Column('mfa_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_audit_logs_status', 'audit_logs', ['status'], unique=False)
    op.create_index('idx_audit_logs_risk', 'audit_logs', ['risk_level'], unique=False)
    op.create_index('idx_audit_logs_created', 'audit_logs', ['created_at'], unique=False)
    op.create_index('idx_audit_logs_ip', 'audit_logs', ['ip_address'], unique=False)
    op.create_index('idx_audit_logs_session', 'audit_logs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('sessions')
    op.drop_table('hosts')
    op.drop_table('groups')
    op.drop_table('users')