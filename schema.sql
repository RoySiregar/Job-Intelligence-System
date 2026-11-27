-- ============================================================
-- Job Intelligence System — Database schema
-- Database : autopilot_jobs_db
-- Engine   : MySQL 8+
--
-- Cara pakai:
--   mysql -u root -p < schema.sql
-- atau import lewat Laragon / HeidiSQL / DBeaver.
--
-- CATATAN:
--  * raw_jobs   = tabel yang DIPAKAI skrip saat ini (scraper, detail, ai_processor, mark_applied).
--  * jobs, job_applications, job_keywords, scrape_runs, dan view = skema "lanjutan (v2)"
--    yang sudah ada di DB tetapi belum dipakai skrip saat ini. Disertakan agar DB bisa
--    direproduksi penuh.
--  * setup_db.sql lama TIDAK lengkap; gunakan file ini.
--  * shelf_locations2 (data lokasi rak) TIDAK terkait proyek ini, sengaja tidak disertakan.
-- ============================================================

CREATE DATABASE IF NOT EXISTS autopilot_jobs_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE autopilot_jobs_db;

-- ============================================================
-- 1) TABEL AKTIF
-- ============================================================
CREATE TABLE IF NOT EXISTS raw_jobs (
  id INT NOT NULL AUTO_INCREMENT,
  job_id VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  company_name VARCHAR(255) DEFAULT NULL,
  location VARCHAR(255) DEFAULT NULL,
  job_url TEXT NOT NULL,
  job_description LONGTEXT,
  skills_required TEXT,
  cover_letter LONGTEXT,
  scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('RAW','HIGH_MATCH','MEDIUM_MATCH','LOW_MATCH','REJECTED','DRAFT_READY','APPLIED') DEFAULT 'RAW',
  applied_at DATETIME DEFAULT NULL,
  match_score INT DEFAULT 0,
  tech_stack TEXT,
  processed_at TIMESTAMP NULL DEFAULT NULL,
  category VARCHAR(100) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY job_id (job_id),
  KEY idx_status (status),
  KEY idx_match_score (match_score),
  KEY idx_processed_at (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 2) SKEMA LANJUTAN (v2) — belum dipakai skrip saat ini
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source ENUM('JOBSTREET','GLINTS','MANUAL') NOT NULL,
  source_job_id VARCHAR(100) NOT NULL,
  title VARCHAR(255) NOT NULL,
  title_normalized VARCHAR(255) DEFAULT NULL COMMENT 'judul setelah prefix SEO dibuang',
  company VARCHAR(255) DEFAULT NULL,
  location VARCHAR(255) DEFAULT NULL,
  url TEXT NOT NULL,
  description LONGTEXT,
  description_hash CHAR(64) DEFAULT NULL,
  match_score INT DEFAULT NULL,
  match_band ENUM('HIGH','MEDIUM','LOW','NONE') DEFAULT NULL,
  score_detail JSON DEFAULT NULL,
  tech_stack JSON DEFAULT NULL,
  status ENUM('NEW','ENRICHED','SCORED','SHORTLISTED','CV_READY','APPLIED','REJECTED','FAILED','DUPLICATE') NOT NULL DEFAULT 'NEW',
  duplicate_of BIGINT UNSIGNED DEFAULT NULL,
  prev_status VARCHAR(20) DEFAULT NULL,
  retry_count TINYINT UNSIGNED NOT NULL DEFAULT '0',
  last_error VARCHAR(500) DEFAULT NULL,
  posted_at DATETIME DEFAULT NULL,
  enriched_at DATETIME DEFAULT NULL,
  scored_at DATETIME DEFAULT NULL,
  shortlisted_at DATETIME DEFAULT NULL,
  cv_ready_at DATETIME DEFAULT NULL,
  applied_at DATETIME DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_jobs_source (source, source_job_id),
  KEY idx_jobs_status (status),
  KEY idx_jobs_band (match_band),
  KEY idx_jobs_score (match_score),
  KEY idx_jobs_hash (description_hash),
  KEY idx_jobs_company (company),
  KEY idx_jobs_pipeline (status, match_score),
  KEY idx_jobs_duplicate (duplicate_of)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_applications (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  cv_path VARCHAR(500) NOT NULL,
  cover_letter LONGTEXT,
  keywords TEXT,
  llm_provider VARCHAR(50) DEFAULT NULL,
  llm_model VARCHAR(100) DEFAULT NULL,
  prompt_version VARCHAR(20) DEFAULT NULL,
  status ENUM('GENERATED','SENT','FAILED') NOT NULL DEFAULT 'GENERATED',
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  applied_at DATETIME DEFAULT NULL,
  error_message VARCHAR(500) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_app_job (job_id),
  KEY idx_app_status (status),
  CONSTRAINT fk_app_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_keywords (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  keyword VARCHAR(100) NOT NULL,
  kind ENUM('ROLE','TECH','INDUSTRY','FRESH_GRAD','NEGATIVE') NOT NULL,
  weight INT NOT NULL DEFAULT '1',
  active TINYINT(1) NOT NULL DEFAULT '1',
  note VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_keyword (keyword, kind),
  KEY idx_kw_kind (kind, active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scrape_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source ENUM('JOBSTREET','GLINTS') NOT NULL,
  started_at DATETIME NOT NULL,
  finished_at DATETIME DEFAULT NULL,
  pages_scraped INT UNSIGNED NOT NULL DEFAULT '0',
  jobs_found INT UNSIGNED NOT NULL DEFAULT '0',
  jobs_inserted INT UNSIGNED NOT NULL DEFAULT '0',
  jobs_duplicate INT UNSIGNED NOT NULL DEFAULT '0',
  jobs_failed INT UNSIGNED NOT NULL DEFAULT '0',
  status ENUM('RUNNING','SUCCESS','PARTIAL','FAILED') NOT NULL DEFAULT 'RUNNING',
  error_message VARCHAR(500) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_runs_source_time (source, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3) VIEWS
-- ============================================================
CREATE OR REPLACE VIEW v_duplicate_jobs AS
select `jobs`.`description_hash` AS `description_hash`,
       count(0) AS `jumlah_baris`,
       group_concat(`jobs`.`id` order by `jobs`.`id` ASC separator ',') AS `job_ids`,
       min(`jobs`.`match_score`) AS `skor_min`,
       max(`jobs`.`match_score`) AS `skor_max`
from `jobs`
where (`jobs`.`description_hash` is not null)
group by `jobs`.`description_hash`
having (count(0) > 1);

CREATE OR REPLACE VIEW v_pipeline_stats AS
select `jobs`.`status` AS `status`,
       count(0) AS `jumlah`,
       round(avg(`jobs`.`match_score`),1) AS `rata2_skor`,
       min(`jobs`.`match_score`) AS `skor_min`,
       max(`jobs`.`match_score`) AS `skor_max`
from `jobs`
group by `jobs`.`status`
order by field(`jobs`.`status`,'NEW','ENRICHED','SCORED','SHORTLISTED','CV_READY','APPLIED','REJECTED','FAILED');

CREATE OR REPLACE VIEW v_shortlist AS
select `jobs`.`id` AS `id`,
       `jobs`.`source` AS `source`,
       `jobs`.`title` AS `title`,
       `jobs`.`company` AS `company`,
       `jobs`.`location` AS `location`,
       `jobs`.`match_score` AS `match_score`,
       `jobs`.`match_band` AS `match_band`,
       `jobs`.`status` AS `status`,
       `jobs`.`url` AS `url`,
       (case when (`jobs`.`match_score` >= 18) then 'HIGH'
             when (`jobs`.`match_score` >= 10) then 'MEDIUM'
             when (`jobs`.`match_score` >= 5) then 'LOW'
             else 'NONE' end) AS `band_if_recalculated`
from `jobs`
where ((`jobs`.`status` in ('SCORED','SHORTLISTED','CV_READY')) and (`jobs`.`duplicate_of` is null))
order by `jobs`.`match_score` desc, `jobs`.`id`;
