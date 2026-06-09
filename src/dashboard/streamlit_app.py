import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from src.core.database import SessionLocal, Application, Job, Analytics
from src.agents.human_approval_agent import HumanApprovalAgent

st.set_page_config(page_title="CareerCopilot AI Dashboard", layout="wide")

def init_db():
    return SessionLocal()

def main():
    st.title("🤖 CareerCopilot AI Dashboard")
    st.markdown("---")
    
    db = init_db()
    approval_agent = HumanApprovalAgent()
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Go to", ["Overview", "Pending Approvals", "Applications", "Analytics", "Settings"])
    
    if page == "Overview":
        st.header("📊 Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Get stats
        total_apps = db.query(Application).count()
        pending_approvals = db.query(Application).filter(Application.approval_status == 'pending').count()
        submitted = db.query(Application).filter(Application.status == 'submitted').count()
        interviews = db.query(Application).join(Application.emails).filter(Email.classification == 'interview').count()
        
        with col1:
            st.metric("Total Applications", total_apps)
        with col2:
            st.metric("Pending Approval", pending_approvals)
        with col3:
            st.metric("Submitted", submitted)
        with col4:
            st.metric("Interviews", interviews)
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_apps = db.query(Application).order_by(Application.created_at.desc()).limit(10).all()
        
        activity_data = []
        for app in recent_apps:
            activity_data.append({
                "Date": app.created_at.strftime("%Y-%m-%d %H:%M"),
                "Company": app.job.company if app.job else "N/A",
                "Role": app.job.title if app.job else "N/A",
                "Match Score": f"{app.match_score:.1f}%" if app.match_score else "N/A",
                "Status": app.status
            })
        
        if activity_data:
            df = pd.DataFrame(activity_data)
            st.dataframe(df, use_container_width=True)
    
    elif page == "Pending Approvals":
        st.header("⏳ Pending Approvals")
        
        pending = approval_agent.get_pending_approvals()
        
        for app in pending:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    st.write(f"**{app['company']}**")
                    st.write(f"_{app['role']}_")
                
                with col2:
                    st.write(f"Match: {app['match_score']:.1f}%")
                    st.write(f"ATS: {app['ats_score']:.1f}%")
                
                with col3:
                    if st.button("✅ Approve", key=f"approve_{app['id']}"):
                        result = approval_agent.process_decision(app['id'], "APPROVE")
                        if result['status'] == 'SUCCESS':
                            st.success("Application approved! It will be submitted shortly.")
                            st.rerun()
                
                with col4:
                    if st.button("⏭️ Skip", key=f"skip_{app['id']}"):
                        result = approval_agent.process_decision(app['id'], "SKIP")
                        if result['status'] == 'SUCCESS':
                            st.warning("Application skipped.")
                            st.rerun()
                
                st.markdown("---")
        
        if not pending:
            st.info("No pending approvals at this time.")
    
    elif page == "Applications":
        st.header("📝 All Applications")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Status", ["All", "pending_approval", "approved", "submitted", "failed"])
        with col2:
            date_filter = st.date_input("From Date", datetime.now() - timedelta(days=30))
        
        query = db.query(Application)
        if status_filter != "All":
            query = query.filter(Application.status == status_filter)
        if date_filter:
            query = query.filter(Application.created_at >= date_filter)
        
        applications = query.order_by(Application.created_at.desc()).all()
        
        for app in applications:
            with st.expander(f"{app.job.company if app.job else 'N/A'} - {app.job.title if app.job else 'N/A'}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Job Details**")
                    st.write(f"Location: {app.job.location if app.job else 'N/A'}")
                    st.write(f"Source: {app.job.source if app.job else 'N/A'}")
                    st.write(f"Match Score: {app.match_score:.1f}%")
                    st.write(f"ATS Score: {app.ats_score:.1f}%")
                
                with col2:
                    st.write("**Application Details**")
                    st.write(f"Status: {app.status}")
                    st.write(f"Created: {app.created_at.strftime('%Y-%m-%d %H:%M')}")
                    if app.submitted_at:
                        st.write(f"Submitted: {app.submitted_at.strftime('%Y-%m-%d %H:%M')}")
                
                if app.missing_keywords:
                    st.write("**Missing Keywords:**")
                    st.write(", ".join(eval(app.missing_keywords)[:10]) if app.missing_keywords else "None")
    
    elif page == "Analytics":
        st.header("📈 Analytics")
        
        # Get analytics data
        analytics_data = db.query(Analytics).order_by(Analytics.period_start.desc()).limit(12).all()
        
        if analytics_data:
            df = pd.DataFrame([{
                "Period": a.period_start.strftime("%Y-%m"),
                "Applications": a.applications_sent,
                "Interviews": a.interviews,
                "Rejections": a.rejections,
                "Offers": a.offers
            } for a in analytics_data])
            
            # Applications trend
            fig1 = px.line(df, x="Period", y="Applications", title="Applications Over Time")
            st.plotly_chart(fig1, use_container_width=True)
            
            # Success rates
            fig2 = px.bar(df, x="Period", y=["Interviews", "Offers"], title="Success Metrics")
            st.plotly_chart(fig2, use_container_width=True)
            
            # Response rate
            df['Response Rate'] = ((df['Interviews'] + df['Rejections']) / df['Applications'] * 100).fillna(0)
            fig3 = px.line(df, x="Period", y="Response Rate", title="Response Rate (%)")
            st.plotly_chart(fig3, use_container_width=True)
    
    elif page == "Settings":
        st.header("⚙️ Settings")
        
        st.subheader("Profile Information")
        with st.form("profile_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            skills = st.text_area("Skills (comma-separated)")
            experience = st.number_input("Years of Experience", min_value=0, max_value=50)
            location = st.text_input("Preferred Location")
            salary = st.text_input("Expected Salary")
            
            if st.form_submit_button("Save Profile"):
                st.success("Profile saved successfully!")
        
        st.subheader("System Settings")
        schedule_interval = st.number_input("Job Search Interval (minutes)", min_value=15, max_value=240, value=30)
        max_applications = st.number_input("Max Applications Per Day", min_value=1, max_value=50, value=20)
        
        if st.button("Update Settings"):
            st.success("Settings updated!")

if __name__ == "__main__":
    main()