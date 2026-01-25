-- 샘플 스키마 생성
CREATE SCHEMA IF NOT EXISTS sample;

-- 직원 테이블
CREATE TABLE sample.employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    position VARCHAR(50),
    salary DECIMAL(10, 2),
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 부서 테이블
CREATE TABLE sample.departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    manager_id INTEGER,
    budget DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 프로젝트 테이블
CREATE TABLE sample.projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INTEGER REFERENCES sample.departments(id),
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    budget DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 샘플 데이터 삽입
INSERT INTO sample.departments (name, budget) VALUES
    ('Engineering', 500000.00),
    ('Marketing', 200000.00),
    ('Sales', 300000.00),
    ('HR', 100000.00);

INSERT INTO sample.employees (name, department, position, salary, hire_date) VALUES
    ('김철수', 'Engineering', 'Senior Developer', 8500000, '2020-03-15'),
    ('이영희', 'Engineering', 'Developer', 6500000, '2021-07-01'),
    ('박민수', 'Marketing', 'Marketing Manager', 7000000, '2019-11-20'),
    ('정지원', 'Sales', 'Sales Representative', 5500000, '2022-01-10'),
    ('최윤정', 'HR', 'HR Specialist', 5000000, '2021-09-05'),
    ('강동현', 'Engineering', 'Tech Lead', 9500000, '2018-06-12'),
    ('윤서영', 'Marketing', 'Content Creator', 4500000, '2023-02-28'),
    ('임재현', 'Sales', 'Account Manager', 6000000, '2020-08-17');

INSERT INTO sample.projects (name, department_id, start_date, end_date, status, budget) VALUES
    ('AI Platform Development', 1, '2024-01-01', '2024-12-31', 'active', 150000000),
    ('Brand Renewal Campaign', 2, '2024-03-01', '2024-06-30', 'completed', 30000000),
    ('Enterprise Sales Expansion', 3, '2024-02-01', NULL, 'active', 50000000),
    ('Employee Training Program', 4, '2024-04-01', '2024-05-31', 'completed', 10000000);

-- 뷰 생성 (부서별 직원 수와 평균 급여)
CREATE VIEW sample.department_stats AS
SELECT 
    department,
    COUNT(*) as employee_count,
    AVG(salary) as avg_salary,
    MIN(salary) as min_salary,
    MAX(salary) as max_salary
FROM sample.employees
GROUP BY department;

GRANT ALL ON SCHEMA sample TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA sample TO postgres;
