import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import re

# הגדרות עמוד
st.set_page_config(page_title="ניהול הכנסות הוצאות", layout="wide")

# עיצוב RTL (מימין לשמאל) כדי שיתאים לעברית
st.markdown("""
<style>
    .main { text-align: right; direction: rtl; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; background-color: #f8f9fb; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    div[data-testid="stMetricValue"] { text-align: right; direction: rtl; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# אתחול הזיכרון (כדי שהנתונים לא יימחקו בזמן הגלישה)
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=['תאריך', 'תיאור', 'סכום', 'קטגוריה'])
if 'fixed_expenses' not in st.session_state:
    st.session_state.fixed_expenses = pd.DataFrame(columns=['תיאור', 'סכום', 'קטגוריה'])

# פונקציה לקריאת קבצי PDF (חשמל, ארנונה וכו')
def process_pdf(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "")
        
        # חיפוש סכומים בקובץ
        amounts = re.findall(r'(\d{2,5}(?:\.\d{2})?)', text)
        amounts = [float(a) for a in amounts if float(a) > 20]
        final_amount = max(amounts) if amounts else 0.0
        
        # זיהוי סוג החשבון לפי מילות מפתח
        desc, cat = "חשבון כללי", "הוצאות בית"
        if "חשמל" in text: desc, cat = "חברת החשמל", "הוצאות בית"
        elif "מים" in text: desc, cat = "חשבון מים", "הוצאות בית"
        elif "ארנונה" in text: desc, cat = "ארנונה", "הוצאות בית"
        elif "רישיון" in text: desc, cat = "רישיון רכב", "תחבורה"
        
        return desc, final_amount, cat
    except:
        return "שגיאה בקריאת הקובץ", 0.0, "שונות"

st.title("💰 ניהול הכנסות הוצאות")

# --- סרגל צדי (Sidebar) ---
with st.sidebar:
    st.header("⚙️ תפריט ניהול")
    
    # הוצאות קבועות - דברים שיורדים כל חודש
    with st.expander("📌 הגדרת הוצאות קבועות"):
        f_desc = st.text_input("שם ההוצאה הקבועה")
        f_amt = st.number_input("סכום חודשי (במינוס)", value=0.0, key="f_amt")
        f_cat = st.selectbox("קטגוריה", ["מגורים", "ביטוחים", "רכב", "מנויים", "אחר"], key="f_cat")
        if st.button("שמור כהוצאה קבועה"):
            new_f = pd.DataFrame([{'תיאור': f_desc, 'סכום': f_amt, 'קטגוריה': f_cat}])
            st.session_state.fixed_expenses = pd.concat([st.session_state.fixed_expenses, new_f], ignore_index=True)
            st.success("ההוצאה הקבועה נשמרה!")

    st.divider()
    
    # העלאת חשבונות ב-PDF
    st.subheader("📸 סריקת חשבון (PDF)")
    uploaded_file = st.file_uploader("גרור לכאן חשבון חשמל/מים", type=['pdf'])
    if uploaded_file:
        d, a, c = process_pdf(uploaded_file)
        st.write(f"🔍 זיהיתי: {d}")
        st.write(f"💰 סכום: ₪{a}")
        if st.button(f"אשר והוסף"):
            new_row = pd.DataFrame([{'תאריך': pd.Timestamp.now(), 'תיאור': d, 'סכום': -a, 'קטגוריה': c}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success("התווסף בהצלחה")

    st.divider()
    
    # הוספה ידנית של הכנסה או הוצאה
    with st.form("manual"):
        st.subheader("➕ הוספה ידנית")
        n_desc = st.text_input("תיאור הקנייה/הכנסה")
        n_amt = st.number_input("סכום (חיובי להכנסה, שלילי להוצאה)", value=0.0)
        n_cat = st.selectbox("קטגוריה", ["הכנסה", "הוצאות בית", "תחבורה", "ילדים", "הלוואות", "שונות"])
        if st.form_submit_button("הוסף לטבלה"):
            new_row = pd.DataFrame([{'תאריך': pd.Timestamp.now(), 'תיאור': n_desc, 'סכום': n_amt, 'קטגוריה': n_cat}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.rerun()

# --- חישובי נתונים ---
fixed_total = st.session_state.fixed_expenses['סכום'].sum()
income = st.session_state.df[st.session_state.df['סכום'] > 0]['סכום'].sum()
variable_expenses = abs(st.session_state.df[st.session_state.df['סכום'] < 0]['סכום'].sum())
total_expenses = variable_expenses + abs(fixed_total)
balance = income - total_expenses

# --- תצוגת המדדים (Metrics) ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("סה\"כ הכנסות", f"₪{income:,.0f}")
col_m2.metric("סה\"כ הוצאות", f"₪{total_expenses:,.0f}", delta=f"₪{abs(fixed_total):,.0f} קבועות")
col_m3.metric("יתרה פנויה", f"₪{balance:,.0f}")

st.divider()

# --- תצוגת התנועות והגרפים ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📝 רשימת תנועות")
    if not st.session_state.df.empty:
        for i, row in st.session_state.df.iterrows():
            with st.expander(f"{row['תאריך'].strftime('%d/%m')} | {row['תיאור']} | ₪{row['סכום']}"):
                st.write(f"קטגוריה: {row['קטגוריה']}")
                if st.button("🗑️ מחק שורה", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i).reset_index(drop=True)
                    st.rerun()
    else:
        st.info("אין עדיין תנועות בטבלה.")

with col_right:
    st.subheader("📊 התפלגות הוצאות")
    if total_expenses > 0:
        # הכנת נתונים לגרף עוגה
        temp_df = st.session_state.df[st.session_state.df['סכום'] < 0].copy()
        if not st.session_state.fixed_expenses.empty:
            temp_df = pd.concat([temp_df, st.session_state.fixed_expenses])
        
        temp_df['סכום'] = temp_df['סכום'].abs()
        fig = px.pie(temp_df, values='סכום', names='קטגוריה', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
# כפתור דוח
if st.button("📧 סיכום רבעוני"):
    st.success("הנתונים מוכנים! ניתן לראות את הסיכום בגרפים ובלוח המדדים למעלה.")
