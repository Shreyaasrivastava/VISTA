"""phase 1 core tables: venues, users, cameras, density_readings

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("role in ('superadmin','admin','security','attendee')", name="ck_users_role"),
        sa.CheckConstraint("role in ('superadmin','attendee') or venue_id is not null", name="ck_users_venue_required"),
    )
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("zone_name", sa.String(80), nullable=False),
        sa.Column("stream_url", sa.String(300), nullable=False),
        sa.Column("ip_address", sa.String(15), nullable=False),
        sa.Column("range_m", sa.Float(), nullable=False),
        sa.Column("th_caution", sa.Float(), nullable=False),
        sa.Column("th_warning", sa.Float(), nullable=False),
        sa.Column("th_critical", sa.Float(), nullable=False),
        sa.Column("zone_polygon", sa.JSON(), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("camera_xy", sa.JSON(), nullable=True),
        sa.Column("homography", sa.JSON(), nullable=True),
        sa.Column("ingest_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("venue_id", "code", name="uq_camera_venue_code"),
    )
    op.create_index("ix_cameras_venue_id", "cameras", ["venue_id"])
    op.create_table(
        "density_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=False),
        sa.Column("density", sa.Float(), nullable=False),
        sa.Column("occupancy_pct", sa.Float(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_density_readings_venue_id", "density_readings", ["venue_id"])
    op.create_index("ix_density_camera_ts", "density_readings", ["camera_id", "ts"])


def downgrade() -> None:
    op.drop_table("density_readings")
    op.drop_table("cameras")
    op.drop_table("users")
    op.drop_table("venues")
