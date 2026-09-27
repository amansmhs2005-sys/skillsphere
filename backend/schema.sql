-- SkillSphere database schema
-- Matches SRS Section 6.1 (Data Requirements), extended with a couple of
-- implementation-level additions noted inline (notifications table,
-- and a few extra columns needed to actually implement REQ-9/REQ-15/REQ-19
-- that the SRS describes at the requirement level but doesn't fully
-- model as columns).

CREATE DATABASE IF NOT EXISTS skillsphere
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE skillsphere;

-- ---------------------------------------------------------------
-- Users  (REQ-1, REQ-2, REQ-3)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id           INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(120) NOT NULL,
    email             VARCHAR(190) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    branch            VARCHAR(100),
    year              VARCHAR(20),
    bio               TEXT,
    is_learner        BOOLEAN NOT NULL DEFAULT TRUE,
    is_tutor          BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin          BOOLEAN NOT NULL DEFAULT FALSE,

    -- Email-link verification (REQ-2). Business rule 5.5: unverified
    -- accounts have read-only access.
    is_verified       BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token VARCHAR(255),

    -- Separate, stronger Admin-performed verification (business rule 5.5:
    -- "Only the Admin role may verify new user accounts"). This is the
    -- "verification status" that feeds 10% of the trust-score formula
    -- (REQ-15) — email verification alone already gates basic access,
    -- so it isn't also the trust-score signal.
    admin_verified    BOOLEAN NOT NULL DEFAULT FALSE,

    -- Admin can suspend an account after reviewing a report (REQ-17).
    is_suspended      BOOLEAN NOT NULL DEFAULT FALSE,

    trust_score       DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Skills & Topics  (REQ-4, REQ-5)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    skill_id      INT AUTO_INCREMENT PRIMARY KEY,
    tutor_id      INT NOT NULL,
    skill_name    VARCHAR(150) NOT NULL,
    topic_name    VARCHAR(150) NOT NULL,
    difficulty    ENUM('beginner', 'intermediate', 'advanced') NOT NULL DEFAULT 'beginner',
    description   TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tutor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_skill_name (skill_name),
    INDEX idx_topic_name (topic_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Availability  (REQ-18, used by AI Recommendation REQ-7)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS availability (
    availability_id INT AUTO_INCREMENT PRIMARY KEY,
    tutor_id        INT NOT NULL,
    day             ENUM('Mon','Tue','Wed','Thu','Fri','Sat','Sun') NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Progress  (REQ-20, REQ-21) — written by Session Management on completion
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS progress (
    progress_id   INT AUTO_INCREMENT PRIMARY KEY,
    learner_id    INT NOT NULL,
    topic_id      INT NOT NULL,
    status        ENUM('pending', 'completed') NOT NULL DEFAULT 'pending',
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (learner_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    UNIQUE KEY uq_learner_topic (learner_id, topic_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Requests & Sessions  (REQ-10 .. REQ-13, REQ-19, plus REQ-9/REQ-21
-- fields needed to actually implement session completion)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requests_sessions (
    request_id          INT AUTO_INCREMENT PRIMARY KEY,
    learner_id           INT NOT NULL,
    tutor_id             INT NOT NULL,
    topic_id             INT NOT NULL,

    problem_description  TEXT,                          -- REQ-10
    mode                 ENUM('online', 'offline') NOT NULL DEFAULT 'online',

    preferred_date       DATE,                           -- learner's ask, REQ-10
    preferred_time       TIME,
    scheduled_date        DATE,                          -- agreed date/time, REQ-12
    scheduled_time        TIME,

    status               ENUM('pending', 'accepted', 'rejected', 'completed', 'cancelled')
                         NOT NULL DEFAULT 'pending',      -- REQ-13
    reject_reason        VARCHAR(255),

    attended             BOOLEAN,                        -- set at completion, feeds REQ-15
    session_notes        TEXT,                           -- tutor notes at close, feeds REQ-9
    session_summary      TEXT,                           -- AI-generated, REQ-9

    reminder_sent        BOOLEAN NOT NULL DEFAULT FALSE,  -- REQ-19 (24h-before reminder)

    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (learner_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (tutor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES skills(skill_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Reviews  (REQ-14, REQ-15)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reviews (
    review_id     INT AUTO_INCREMENT PRIMARY KEY,
    session_id    INT NOT NULL UNIQUE,
    rating        TINYINT NOT NULL,
    feedback      TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES requests_sessions(request_id) ON DELETE CASCADE,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Reports  (REQ-17, REQ-22)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    report_id     INT AUTO_INCREMENT PRIMARY KEY,
    session_id    INT NOT NULL,
    reported_by   INT NOT NULL,
    reason        TEXT NOT NULL,
    status        ENUM('open', 'reviewed', 'dismissed') NOT NULL DEFAULT 'open',
    admin_action  VARCHAR(255),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at   TIMESTAMP NULL,
    FOREIGN KEY (session_id) REFERENCES requests_sessions(request_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Notifications (implementation detail supporting REQ-19's
-- "notify a user in-app" requirement — not itemised as its own
-- entity in SRS Section 6.1, added here to make REQ-19 concrete)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    type             VARCHAR(50) NOT NULL,   -- e.g. session_requested, session_accepted, reminder
    message          TEXT NOT NULL,
    related_id       INT,                    -- e.g. request_id
    is_read          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- Search history (implementation detail supporting REQ-8's
-- "related topics based on ... search history")
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_history (
    search_id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id            INT NOT NULL,
    query_text         TEXT NOT NULL,
    detected_skill_id  INT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (detected_skill_id) REFERENCES skills(skill_id) ON DELETE SET NULL
) ENGINE=InnoDB;
