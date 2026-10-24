ALTER TABLE return_request
    ADD COLUMN inspection_registration_state varchar(24) NOT NULL DEFAULT 'PENDING'
        CHECK (inspection_registration_state IN ('PENDING','REGISTERED','MANUAL_REVIEW')),
    ADD COLUMN inspection_lease_owner varchar(160),
    ADD COLUMN inspection_lease_until timestamptz,
    ADD COLUMN inspection_next_attempt_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN inspection_attempt integer NOT NULL DEFAULT 0,
    ADD COLUMN inspection_error_code varchar(80);

CREATE INDEX return_inspection_registration_idx ON return_request(inspection_next_attempt_at,created_at)
    WHERE status='COMPLETED' AND inspection_registration_state='PENDING';
