-- Booking-risk schema. The app creates the same tables via SQLAlchemy.
-- account_parties.kind is 'exception' or 'known_payer'.
-- reviews.action is 'release', 'uphold', or 'block'.
-- assessments.decision is 'allow', 'step-up', 'hold', or 'block'.

CREATE TABLE accounts (
    account_number          VARCHAR(16) PRIMARY KEY,
    name                    VARCHAR(120) NOT NULL,
    status                  VARCHAR(16)  NOT NULL,
    inbound_policy          VARCHAR(32)  NOT NULL,
    mostly_domestic_ground  BOOLEAN      NOT NULL,
    weekly_pace             REAL         NOT NULL,
    median_weight_kg        REAL         NOT NULL,
    shipment_count_90d      INTEGER      NOT NULL
);

CREATE TABLE account_postals (
    id               INTEGER PRIMARY KEY,
    account_number   VARCHAR(16) NOT NULL REFERENCES accounts(account_number),
    postal_code      VARCHAR(16) NOT NULL,
    country_code     VARCHAR(2)  NOT NULL DEFAULT 'IN'
);

CREATE TABLE account_users (
    id               INTEGER PRIMARY KEY,
    account_number   VARCHAR(16) NOT NULL REFERENCES accounts(account_number),
    ups_user_id      VARCHAR(64) NOT NULL
);

CREATE TABLE account_parties (
    id               INTEGER PRIMARY KEY,
    account_number   VARCHAR(16) NOT NULL REFERENCES accounts(account_number),
    shipper_number   VARCHAR(16) NOT NULL,
    kind             VARCHAR(16) NOT NULL
);

CREATE TABLE booking_attempts (
    id               INTEGER PRIMARY KEY,
    account_number   VARCHAR(16) NOT NULL,
    tx_id            VARCHAR(64),
    created_at       TIMESTAMP NOT NULL
);

CREATE INDEX ix_attempts_account_time ON booking_attempts (account_number, created_at);

CREATE TABLE assessments (
    id                   INTEGER PRIMARY KEY,
    tx_id                VARCHAR(64) NOT NULL UNIQUE,
    created_at           TIMESTAMP NOT NULL,
    channel              VARCHAR(32) NOT NULL,
    payment_type         VARCHAR(32) NOT NULL,
    billed_account       VARCHAR(16),
    shipper_account      VARCHAR(16),
    guest                BOOLEAN NOT NULL,
    ups_user_id          VARCHAR(64),
    ship_from_postal     VARCHAR(16) NOT NULL,
    ship_from_country    VARCHAR(2)  NOT NULL,
    ship_to_postal       VARCHAR(16) NOT NULL,
    ship_to_country      VARCHAR(2)  NOT NULL,
    weight_kg            REAL NOT NULL,
    service              VARCHAR(32) NOT NULL,
    decision             VARCHAR(16) NOT NULL,
    score                REAL NOT NULL,
    policy_version       VARCHAR(32) NOT NULL,
    explanation          TEXT NOT NULL,
    explanation_source   VARCHAR(16) NOT NULL,
    features_json        TEXT NOT NULL,
    recent_bookings_1h   INTEGER NOT NULL
);

CREATE TABLE assessment_reasons (
    id               INTEGER PRIMARY KEY,
    assessment_id    INTEGER NOT NULL REFERENCES assessments(id),
    position         INTEGER NOT NULL,
    code             VARCHAR(64) NOT NULL
);

CREATE TABLE reviews (
    id               INTEGER PRIMARY KEY,
    assessment_id    INTEGER NOT NULL REFERENCES assessments(id),
    created_at       TIMESTAMP NOT NULL,
    reviewer         VARCHAR(64) NOT NULL,
    action           VARCHAR(16) NOT NULL,
    note             TEXT NOT NULL DEFAULT ''
);
