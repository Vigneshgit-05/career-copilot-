from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from src.core.config import settings

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    profiles = relationship("Profile", back_populates="user")
    applications = relationship("Application", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    skills = Column(Text)  # JSON string
    experience = Column(Text)  # JSON string
    education = Column(Text)  # JSON string
    certifications = Column(Text)  # JSON string
    preferred_location = Column(String(255))
    expected_salary = Column(String(100))
    notice_period = Column(String(50))
    linkedin_url = Column(String(500))
    github_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="profiles")

class Resume(Base):
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True)
    drive_file_id = Column(String(255), unique=True)
    filename = Column(String(255))
    file_type = Column(String(50))
    extracted_text = Column(Text)
    skills = Column(Text)  # JSON string
    projects = Column(Text)  # JSON string
    experience = Column(Text)  # JSON string
    certifications = Column(Text)  # JSON string
    embedding = Column(Text)  # JSON string for vector
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True)
    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    description = Column(Text)
    requirements = Column(Text)  # JSON string
    skills = Column(Text)  # JSON string
    ats_keywords = Column(Text)  # JSON string
    source = Column(String(100))
    discovered_at = Column(DateTime, default=datetime.utcnow)
    
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    
    match_score = Column(Float)
    ats_score = Column(Float)
    selected_resume = Column(String(255))
    missing_keywords = Column(Text)
    
    status = Column(String(50))  # pending_approval, approved, rejected, submitted, failed
    approval_status = Column(String(50))  # pending, approved, skipped, saved_for_later
    submission_evidence = Column(Text)  # JSON with screenshot path
    submission_status = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime)
    
    job = relationship("Job", back_populates="applications")
    user = relationship("User", back_populates="applications")
    resume = relationship("Resume")
    emails = relationship("Email", back_populates="application")

class Email(Base):
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'))
    message_id = Column(String(255), unique=True)
    from_address = Column(String(255))
    subject = Column(String(500))
    body = Column(Text)
    classification = Column(String(50))  # confirmation, interview, assessment, rejection, offer
    created_at = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="emails")

class Analytics(Base):
    __tablename__ = 'analytics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    period_type = Column(String(50))  # daily, weekly, monthly
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    applications_sent = Column(Integer, default=0)
    interviews = Column(Integer, default=0)
    rejections = Column(Integer, default=0)
    offers = Column(Integer, default=0)
    response_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create engine and tables
engine = create_engine(f'sqlite:///{settings.DATABASE_PATH}', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()