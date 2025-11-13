-- Boostly relational schema targeting PostgreSQL 14+
-- Runs inside the "public" schema unless overridden. Extensions must be installed by a superuser.

-- id generation and case-insensitive text helpers
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- exposes gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";   -- provides citext for case-insensitive comparisons

-- Enumerations constrain allowed status values and tighten validation at the database layer.
CREATE TYPE credit_event_type AS ENUM (
    'RECOGNITION_SENT',      -- negative delta on sender ledger
    'RECOGNITION_RECEIVED',  -- positive delta on receiver ledger
    'REDEMPTION',            -- negative delta when vouchers are issued
    'MONTHLY_RESET',         -- baseline monthly credit grant
    'CARRY_FORWARD',         -- carry-forward allocation applied to the new month
    'CARRY_FORWARD_EXPIRED'  -- negative delta removing unused allocation beyond carry cap
);

CREATE TYPE redemption_status AS ENUM ('PENDING', 'ISSUED', 'FAILED', 'CANCELLED');

-- Core student directory / profile
CREATE TABLE students (
    student_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campus_uid      TEXT        NOT NULL,
    email           CITEXT      NOT NULL,
    display_name    TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT students_campus_uid_unique UNIQUE (campus_uid)
);

CREATE UNIQUE INDEX students_email_ci_unique ON students (email);
CREATE INDEX students_status_idx ON students (status);

-- Recognition events transfer credits from sender to receiver.
CREATE TABLE recognitions (
    recognition_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id           UUID        NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    receiver_id         UUID        NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    credits_transferred INTEGER     NOT NULL CHECK (credits_transferred > 0),
    message             TEXT,
    month_bucket        DATE        NOT NULL, -- first day of month derived during write, supports monthly analytics
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    endorsement_count   INTEGER     NOT NULL DEFAULT 0,
    recognition_count   INTEGER     NOT NULL DEFAULT 1, -- always 1, retained for leaderboard joins
    CONSTRAINT recognitions_sender_receiver_check CHECK (sender_id <> receiver_id)
);

CREATE INDEX recognitions_sender_idx ON recognitions (sender_id, month_bucket);
CREATE INDEX recognitions_receiver_idx ON recognitions (receiver_id, month_bucket DESC, created_at DESC);
CREATE INDEX recognitions_month_idx ON recognitions (month_bucket);

-- Endorsements register single cheers per student per recognition.
CREATE TABLE recognition_endorsements (
    endorsement_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recognition_id  UUID        NOT NULL REFERENCES recognitions(recognition_id) ON DELETE RESTRICT,
    endorser_id     UUID        NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT recognition_endorsements_unique UNIQUE (recognition_id, endorser_id)
);

CREATE INDEX recognition_endorsements_endorser_idx ON recognition_endorsements (endorser_id, created_at DESC);

-- Redemptions convert earned credits into vouchers at decisioned value.
CREATE TABLE redemptions (
    redemption_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id        UUID            NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    credits_redeemed  INTEGER         NOT NULL CHECK (credits_redeemed > 0),
    voucher_value     INTEGER         GENERATED ALWAYS AS (credits_redeemed * 5) STORED,
    status            redemption_status NOT NULL DEFAULT 'PENDING',
    reference_code    TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    fulfilled_at      TIMESTAMPTZ,
    issued_by         TEXT
);

CREATE INDEX redemptions_student_idx ON redemptions (student_id, created_at DESC);
CREATE INDEX redemptions_status_idx ON redemptions (status);

-- Ledger captures every credit movement; balances are derived via SUM(credits_delta).
CREATE TABLE credit_ledger (
    ledger_entry_id     BIGSERIAL PRIMARY KEY,
    student_id          UUID            NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    related_recognition UUID            REFERENCES recognitions(recognition_id) ON DELETE SET NULL,
    related_redemption  UUID            REFERENCES redemptions(redemption_id) ON DELETE SET NULL,
    quota_snapshot_id   UUID,
    event_type          credit_event_type NOT NULL,
    credits_delta       INTEGER         NOT NULL CHECK (credits_delta <> 0),
    month_bucket        DATE            NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    running_balance     INTEGER,
    CONSTRAINT credit_ledger_delta_sign CHECK (
        (event_type IN ('RECOGNITION_SENT', 'REDEMPTION', 'CARRY_FORWARD_EXPIRED') AND credits_delta < 0) OR
        (event_type IN ('RECOGNITION_RECEIVED', 'MONTHLY_RESET', 'CARRY_FORWARD') AND credits_delta > 0)
    )
);

CREATE INDEX credit_ledger_student_month_idx ON credit_ledger (student_id, month_bucket);
CREATE INDEX credit_ledger_student_created_idx ON credit_ledger (student_id, created_at DESC);
CREATE INDEX credit_ledger_recognition_idx ON credit_ledger (related_recognition);

-- Monthly quota tracks per-student send limit usage and carry-forward details.
CREATE TABLE monthly_quota (
    quota_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id           UUID        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    month_bucket         DATE        NOT NULL,
    credits_sent         INTEGER     NOT NULL DEFAULT 0 CHECK (credits_sent >= 0),
    send_limit           INTEGER     NOT NULL DEFAULT 100 CHECK (send_limit >= 0),
    carry_forward_applied BOOLEAN    NOT NULL DEFAULT FALSE,
    carry_forward_credits INTEGER    NOT NULL DEFAULT 0 CHECK (carry_forward_credits BETWEEN 0 AND 50),
    reset_at             TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT monthly_quota_unique UNIQUE (student_id, month_bucket)
);

CREATE INDEX monthly_quota_month_idx ON monthly_quota (month_bucket, send_limit);

-- Audit each monthly reset execution for troubleshooting and replay safety.
CREATE TABLE monthly_reset_audit (
    reset_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month_bucket    DATE        NOT NULL,
    student_id      UUID        REFERENCES students(student_id) ON DELETE CASCADE,
    baseline_grant  INTEGER     NOT NULL DEFAULT 100,
    carry_forward   INTEGER     NOT NULL DEFAULT 0,
    capped_amount   INTEGER     NOT NULL DEFAULT 0,
    processed_by    TEXT,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX monthly_reset_audit_month_idx ON monthly_reset_audit (month_bucket);
CREATE INDEX monthly_reset_audit_student_idx ON monthly_reset_audit (student_id, processed_at DESC);

-- Derived balances: view to expose current available credits per student, subtracting any in-flight redemption holds.
CREATE VIEW student_credit_balances AS
SELECT
    s.student_id,
    COALESCE(SUM(cl.credits_delta), 0) AS current_balance
FROM students s
LEFT JOIN credit_ledger cl ON cl.student_id = s.student_id
GROUP BY s.student_id;

-- Entity-Relationship overview (textual):
--
-- students (1) ──< recognitions.sender_id
-- students (1) ──< recognitions.receiver_id
-- recognitions (1) ──< recognition_endorsements.recognition_id
-- students (1) ──< recognition_endorsements.endorser_id
-- students (1) ──< redemptions.student_id
-- recognitions (1) ──< credit_ledger.related_recognition
-- redemptions (1) ──< credit_ledger.related_redemption
-- students (1) ──< credit_ledger.student_id
-- students (1) ──< monthly_quota.student_id
-- students (1) ──< monthly_reset_audit.student_id

-- SQLAlchemy ORM relationship sketch:
-- class Student(Base):
--     __tablename__ = "students"
--     recognitions_sent = relationship("Recognition", foreign_keys="Recognition.sender_id", back_populates="sender")
--     recognitions_received = relationship("Recognition", foreign_keys="Recognition.receiver_id", back_populates="receiver")
--     endorsements = relationship("RecognitionEndorsement", back_populates="endorser")
--     redemptions = relationship("Redemption", back_populates="student")
--     ledger_entries = relationship("CreditLedger", back_populates="student")
--
-- class Recognition(Base):
--     __tablename__ = "recognitions"
--     sender = relationship("Student", foreign_keys=[sender_id], back_populates="recognitions_sent")
--     receiver = relationship("Student", foreign_keys=[receiver_id], back_populates="recognitions_received")
--     endorsements = relationship("RecognitionEndorsement", back_populates="recognition")
--     debit_entries = relationship("CreditLedger", back_populates="recognition", foreign_keys="CreditLedger.related_recognition")
--
-- class RecognitionEndorsement(Base):
--     __tablename__ = "recognition_endorsements"
--     recognition = relationship("Recognition", back_populates="endorsements")
--     endorser = relationship("Student", back_populates="endorsements")
--
-- class Redemption(Base):
--     __tablename__ = "redemptions"
--     student = relationship("Student", back_populates="redemptions")
--     ledger_entries = relationship("CreditLedger", back_populates="redemption")
--
-- class CreditLedger(Base):
--     __tablename__ = "credit_ledger"
--     student = relationship("Student", back_populates="ledger_entries")
--     recognition = relationship("Recognition", back_populates="debit_entries")
--     redemption = relationship("Redemption", back_populates="ledger_entries")

-- Seed data for demonstration/testing ------------------------------------------------------------
INSERT INTO students (student_id, campus_uid, email, display_name)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'S1001', 'alex.rao@example.edu', 'Alex Rao'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'S1002', 'bianca.liu@example.edu', 'Bianca Liu'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'S1003', 'carlos.menon@example.edu', 'Carlos Menon')
ON CONFLICT (campus_uid) DO NOTHING;

-- Baseline monthly reset for November 2025
INSERT INTO monthly_quota (quota_id, student_id, month_bucket, credits_sent)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', DATE '2025-11-01', 0),
    ('22222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', DATE '2025-11-01', 0),
    ('33333333-3333-3333-3333-333333333333', 'cccccccc-cccc-cccc-cccc-cccccccccccc', DATE '2025-11-01', 0)
ON CONFLICT (student_id, month_bucket) DO NOTHING;

-- Grant monthly baseline credits via ledger entries
INSERT INTO credit_ledger (student_id, event_type, credits_delta, month_bucket)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'MONTHLY_RESET', 100, DATE '2025-11-01'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'MONTHLY_RESET', 100, DATE '2025-11-01'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'MONTHLY_RESET', 100, DATE '2025-11-01');

-- Recognition: Alex sends Bianca 30 credits
INSERT INTO recognitions (recognition_id, sender_id, receiver_id, credits_transferred, message, month_bucket)
VALUES
    ('44444444-4444-4444-4444-444444444444', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 30, 'Thanks for leading the robotics workshop!', DATE '2025-11-01'),
    ('55555555-5555-5555-5555-555555555555', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 20, 'Appreciate your help with the lab prep!', DATE '2025-11-01');

-- Ledger entries reflecting recognition transfer
INSERT INTO credit_ledger (student_id, related_recognition, event_type, credits_delta, month_bucket)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '44444444-4444-4444-4444-444444444444', 'RECOGNITION_SENT', -30, DATE '2025-11-01'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '44444444-4444-4444-4444-444444444444', 'RECOGNITION_RECEIVED', 30, DATE '2025-11-01'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '55555555-5555-5555-5555-555555555555', 'RECOGNITION_SENT', -20, DATE '2025-11-01'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', '55555555-5555-5555-5555-555555555555', 'RECOGNITION_RECEIVED', 20, DATE '2025-11-01');

-- Recognition endorsements
INSERT INTO recognition_endorsements (endorsement_id, recognition_id, endorser_id)
VALUES
    ('66666666-6666-6666-6666-666666666666', '44444444-4444-4444-4444-444444444444', 'cccccccc-cccc-cccc-cccc-cccccccccccc'),
    ('77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
ON CONFLICT DO NOTHING;

-- Update endorsement counters in recognitions (optional seed step)
UPDATE recognitions
SET endorsement_count = (SELECT COUNT(*) FROM recognition_endorsements re WHERE re.recognition_id = recognitions.recognition_id)
WHERE recognition_id IN ('44444444-4444-4444-4444-444444444444', '55555555-5555-5555-5555-555555555555');

