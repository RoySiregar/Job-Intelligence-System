-- 1. Membuat Database
CREATE DATABASE IF NOT EXISTS autopilot_jobs_db;
USE autopilot_jobs_db;

-- 2. Membuat Tabel Utama Lowongan
CREATE TABLE IF NOT EXISTS raw_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    job_description TEXT NOT NULL,
    
    -- Kolom untuk hasil olahan AI
    skills_required TEXT, -- Untuk menyimpan keyword ekstraksi AI
    cover_letter TEXT,    -- Untuk menyimpan draft cover letter
    
    -- Status Alur Kerja
    -- DRAFT_READY: Siap diproses AI
    -- APPLIED: Sudah dibuatkan CV & Cover Letter
    -- FAILED: Terjadi error saat proses
    status ENUM('DRAFT_READY', 'APPLIED', 'FAILED') DEFAULT 'DRAFT_READY',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 3. Contoh Data Dummy (Opsional - untuk testing)
INSERT INTO raw_jobs (title, company_name, job_description, status) 
VALUES (
    'Backend Engineer (.NET)', 
    'Tech Global Corp', 
    'Looking for a developer experienced in C#, .NET Core, and MySQL for Industrial IoT projects.', 
    'DRAFT_READY'
);