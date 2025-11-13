import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_FILE = "clubdata.db"
SUPABASE_URL = os.getenv("SUPABASE_URL")
POSTGRES_URL = os.getenv("POSTGRES_URL")

# ---------- Database helpers ----------
def run_query(query, params=()):
    """Execute a query without returning results"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def fetch_df(query, params=()):
    """Fetch query results as DataFrame"""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()
    return df

def get_db_connection():
    """Create a connection to Supabase PostgreSQL"""
    return psycopg2.connect(POSTGRES_URL)

# ---------- Initialize database ----------
def init_db():
    """Create tables if they don't exist"""
    run_query("""
        CREATE TABLE IF NOT EXISTS people (
            id SERIAL PRIMARY KEY,
            last_name TEXT,
            first_name TEXT,
            phone TEXT,
            email TEXT,
            is_member TEXT,
            member_month TEXT,
            member_year INTEGER,
            subscription_year INTEGER,
            is_athlete TEXT,
            eom_number TEXT,
            athlete_from_year INTEGER,
            is_student TEXT,
            student_period_month TEXT,
            student_period_year INTEGER,
            student_university TEXT,
            is_interested TEXT,
            interested_from_month TEXT,
            interested_from_year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            club_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS custom_fields (
            id SERIAL PRIMARY KEY,
            field_name TEXT UNIQUE,
            display_name TEXT,
            applicable_domains TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS member_attributes (
            id SERIAL PRIMARY KEY,
            member_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
            field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
            field_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

init_db()

# ---------- Settings ----------
def get_club_name():
    df = fetch_df("SELECT club_name FROM settings LIMIT 1")
    return df["club_name"].iloc[0] if not df.empty else None

def set_club_name(name):
    run_query("DELETE FROM settings")
    run_query("INSERT INTO settings (club_name) VALUES (%s)", (name,))

# ---------- Export helpers ----------
def excel_bytes_from_df(df_input, sheet_name="Μέλη"):
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_input.to_excel(writer, index=False, sheet_name=sheet_name)
    return excel_buffer.getvalue()

def generate_excel_filename(prefix="data"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.xlsx"

# ---------- Custom fields helper functions ----------
def get_custom_fields():
    return fetch_df("SELECT * FROM custom_fields ORDER BY id")

def get_member_attributes(member_id):
    query = """
        SELECT cf.id, cf.field_name, cf.display_name, ma.field_value
        FROM member_attributes ma
        JOIN custom_fields cf ON ma.field_id = cf.id
        WHERE ma.member_id = %s
    """
    return fetch_df(query, (member_id,))

def save_member_attribute(member_id, field_id, field_value):
    existing = fetch_df("SELECT id FROM member_attributes WHERE member_id=%s AND field_id=%s", (member_id, field_id))
    if existing.empty:
        run_query("INSERT INTO member_attributes (member_id, field_id, field_value) VALUES (%s,%s,%s)", (member_id, field_id, field_value))
    else:
        run_query("UPDATE member_attributes SET field_value=%s WHERE member_id=%s AND field_id=%s", (field_value, member_id, field_id))

def add_custom_field(field_name, display_name, applicable_domains):
    domains_str = ",".join(applicable_domains) if applicable_domains else "Όλα"
    run_query("INSERT INTO custom_fields (field_name, display_name, applicable_domains) VALUES (%s,%s,%s)", 
              (field_name, display_name, domains_str))

def delete_custom_field(field_id):
    run_query("DELETE FROM member_attributes WHERE field_id=%s", (field_id,))
    run_query("DELETE FROM custom_fields WHERE id=%s", (field_id,))

def get_custom_fields_by_domain(domain):
    """Returns custom fields applicable to a specific domain"""
    all_custom = get_custom_fields()
    if all_custom.empty:
        return all_custom
    applicable = all_custom[
        (all_custom["applicable_domains"] == "Όλα") | 
        (all_custom["applicable_domains"].str.contains(domain, na=False))
    ]
    return applicable

# ---------- Page setup ----------
st.set_page_config(page_title="Εφαρμογή Ομίλου Μπριτζ", layout="wide")

months = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
          "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]
years_2000_2050 = list(range(2000,2051))
years_2010_2050 = list(range(2010,2051))
years_1980_2050 = list(range(1980,2051))
years_2018_2050 = list(range(2018,2051))

# ---------- App ----------
club_name = get_club_name()

if not club_name:
    st.title("🎴 Καλώς ήρθατε!")
    st.subheader("Ορίστε το όνομα του Ομίλου σας για πρώτη φορά:")
    new_name = st.text_input("Όνομα Ομίλου", value="ΟΜΗ")
    if st.button("Αποθήκευση"):
        set_club_name(new_name.strip())
        st.success(f"✅ Το όνομα '{new_name}' αποθηκεύτηκε! Επανεκκινήστε την εφαρμογή.")
        st.stop()
else:
    st.title(f"🃏 {club_name}")
    st.markdown("### Κεντρική Διαχείριση Μελών")

    df_all = fetch_df("SELECT * FROM people")
    counts = {
        "members": df_all[df_all["is_member"]=="ΝΑΙ"].shape[0],
        "athletes": df_all[df_all["is_athlete"]=="ΝΑΙ"].shape[0],
        "students": df_all[df_all["is_student"]=="ΝΑΙ"].shape[0],
        "interested": df_all[df_all["is_interested"]=="ΝΑΙ"].shape[0],
        "all": df_all.shape[0]
    }

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "Εισαγωγή Νέου Μέλους",
        f"Μέλη ({counts['members']})",
        f"Αθλητές ({counts['athletes']})",
        f"Μαθητές ({counts['students']})",
        f"Ενδιαφερόμενοι ({counts['interested']})",
        f"Όλα ({counts['all']})",
        "Ρυθμίσεις",
        "📥 Εισαγωγή Δεδομένων",
        "⚙️ Διαχείριση Πεδίων"
    ])

    # ---------- Tab1: Add new member ----------
    with tab1:
        st.header("➕ Εισαγωγή Νέου Μέλους")
        with st.expander("🪪 ΓΕΝΙΚΑ ΣΤΟΙΧΕΙΑ", expanded=True):
            last_name = st.text_input("Επώνυμο", key="new_last_name")
            first_name = st.text_input("Όνομα", key="new_first_name")
            phone = st.text_input("Τηλέφωνο", key="new_phone")
            email = st.text_input("Email", key="new_email")
            
            general_custom_fields = get_custom_fields_by_domain("ΓΕΝΙΚΑ ΣΤΟΙΧΕΙΑ")
            general_custom_inputs = {}
            if not general_custom_fields.empty:
                st.markdown("##### Επιπλέον Πληροφορίες")
                for _, field in general_custom_fields.iterrows():
                    value = st.text_input(field["display_name"], key=f"new_general_{field['field_name']}")
                    general_custom_inputs[field['field_name']] = value

        with st.expander("🧑‍🤝‍🧑 ΜΕΛΟΣ"):
            is_member = st.selectbox("Εγγραφή ως μέλος;", ["ΟΧΙ", "ΝΑΙ"], key="new_is_member")
            col1, col2 = st.columns(2)
            with col1:
                member_month = st.selectbox("Αρχική Εγγραφή - Μήνας", months, key="new_member_month")
            with col2:
                member_year = st.selectbox("Αρχική Εγγραφή - Έτος", years_2000_2050, key="new_member_year")
            subscription_year = st.selectbox("Συνδρομή για Έτος", years_2010_2050, key="new_subscription_year")
            
            member_custom_fields = get_custom_fields_by_domain("ΜΕΛΟΣ")
            member_custom_inputs = {}
            if not member_custom_fields.empty:
                st.markdown("##### Επιπλέον Πληροφορίες Μέλους")
                for _, field in member_custom_fields.iterrows():
                    value = st.text_input(field["display_name"], key=f"new_member_{field['field_name']}")
                    member_custom_inputs[field['field_name']] = value

        with st.expander("🏅 ΑΘΛΗΤΗΣ"):
            is_athlete = st.selectbox("Είναι Αθλητής;", ["ΟΧΙ", "ΝΑΙ"], key="new_is_athlete")
            eom_number = st.text_input("ΑΜ ΕΟΜ", key="new_eom_number")
            athlete_from_year = st.selectbox("Από Έτος", years_1980_2050, key="new_athlete_from_year")
            
            athlete_custom_fields = get_custom_fields_by_domain("ΑΘΛΗΤΗΣ")
            athlete_custom_inputs = {}
            if not athlete_custom_fields.empty:
                st.markdown("##### Επιπλέον Πληροφορίες Αθλητή")
                for _, field in athlete_custom_fields.iterrows():
                    value = st.text_input(field["display_name"], key=f"new_athlete_{field['field_name']}")
                    athlete_custom_inputs[field['field_name']] = value

        with st.expander("🎓 ΜΑΘΗΤΗΣ"):
            is_student = st.selectbox("Είναι Μαθητής;", ["ΟΧΙ", "ΝΑΙ"], key="new_is_student")
            col3, col4 = st.columns(2)
            with col3:
                student_period_month = st.selectbox("Περίοδος - Μήνας", months, key="new_student_period_month")
            with col4:
                student_period_year = st.selectbox("Περίοδος - Έτος", years_2010_2050, key="new_student_period_year")
            student_university = st.selectbox("Πανεπιστήμιο;", ["ΟΧΙ", "ΝΑΙ"], key="new_student_university")
            
            student_custom_fields = get_custom_fields_by_domain("ΜΑΘΗΤΗΣ")
            student_custom_inputs = {}
            if not student_custom_fields.empty:
                st.markdown("##### Επιπλέον Πληροφορίες Μαθητή")
                for _, field in student_custom_fields.iterrows():
                    value = st.text_input(field["display_name"], key=f"new_student_{field['field_name']}")
                    student_custom_inputs[field['field_name']] = value

        with st.expander("👀 ΕΝΔΙΑΦΕΡΟΜΕΝΟΣ"):
            is_interested = st.selectbox("Είναι Ενδιαφερόμενος;", ["ΟΧΙ", "ΝΑΙ"], key="new_is_interested")
            col5, col6 = st.columns(2)
            with col5:
                interested_from_month = st.selectbox("Από - Μήνας", months, key="new_interested_from_month")
            with col6:
                interested_from_year = st.selectbox("Από - Έτος", years_2018_2050, key="new_interested_from_year")
            
            interested_custom_fields = get_custom_fields_by_domain("ΕΝΔΙΑΦΕΡΟΜΕΝΟΣ")
            interested_custom_inputs = {}
            if not interested_custom_fields.empty:
                st.markdown("##### Επιπλέον Πληροφορίες Ενδιαφερόμενου")
                for _, field in interested_custom_fields.iterrows():
                    value = st.text_input(field["display_name"], key=f"new_interested_{field['field_name']}")
                    interested_custom_inputs[field['field_name']] = value

        if st.button("💾 Αποθήκευση Μέλους"):
            if not last_name or not first_name:
                st.warning("⚠️ Συμπληρώστε τουλάχιστον Επώνυμο και Όνομα.")
            else:
                run_query("""
                    INSERT INTO people (
                        last_name, first_name, phone, email, is_member, member_month,
                        member_year, subscription_year, is_athlete, eom_number, athlete_from_year,
                        is_student, student_period_month, student_period_year, student_university,
                        is_interested, interested_from_month, interested_from_year
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    last_name, first_name, phone, email, is_member, member_month,
                    member_year, subscription_year, is_athlete, eom_number, athlete_from_year,
                    is_student, student_period_month, student_period_year, student_university,
                    is_interested, interested_from_month, interested_from_year
                ))
                member_id = fetch_df("SELECT id FROM people WHERE email=%s AND first_name=%s AND last_name=%s", (email, first_name, last_name))["id"].iloc[0]
                
                all_custom_inputs = {**general_custom_inputs, **member_custom_inputs, **athlete_custom_inputs, **student_custom_inputs, **interested_custom_inputs}
                for field_name, value in all_custom_inputs.items():
                    if value:  # Only save if value is not empty
                        field_id = fetch_df("SELECT id FROM custom_fields WHERE field_name=%s", (field_name,))["id"].iloc[0]
                        save_member_attribute(member_id, field_id, value)
                
                st.success(f"✅ Το μέλος {first_name} {last_name} αποθηκεύτηκε επιτυχώς!")
                st.rerun()

    # ---------- Tabs 2-5: expandable, read-only ----------
    def display_expandable_info(df, title):
        st.header(title)
        if df.empty:
            st.info("Δεν υπάρχουν εγγραφές για εμφάνιση.")
            return
        for _, row in df.iterrows():
            with st.expander(f"{row['first_name']} {row['last_name']}"):
                st.write(f"Τηλέφωνο: {row.get('phone') or '-'}")
                st.write(f"Email: {row.get('email') or '-'}")
                st.write(f"Μέλος: {row.get('is_member')} (Συνδρ.: {row.get('subscription_year') or '-'})")
                st.write(f"Αθλητής: {row.get('is_athlete')} (Από: {row.get('athlete_from_year') or '-'})")
                st.write(f"Μαθητής: {row.get('is_student')} (Έτος: {row.get('student_period_year') or '-'})")
                st.write(f"Ενδιαφερόμενος: {row.get('is_interested')}")
                # Display custom fields
                custom_attrs = get_member_attributes(row["id"])
                for _, attr in custom_attrs.iterrows():
                    st.write(f"{attr['display_name']}: {attr['field_value'] or '-'}")

    with tab2:
        display_expandable_info(df_all[df_all["is_member"]=="ΝΑΙ"], "🧑‍🤝‍🧑 Μέλη")

    with tab3:
        display_expandable_info(df_all[df_all["is_athlete"]=="ΝΑΙ"], "🏅 Αθλητές")

    with tab4:
        display_expandable_info(df_all[df_all["is_student"]=="ΝΑΙ"], "🎓 Μαθητές")

    with tab5:
        display_expandable_info(df_all[df_all["is_interested"]=="ΝΑΙ"], "👀 Ενδιαφερόμενοι")

    # ---------- Tab6: Editable all entries ----------
    def display_editable_all(df, tab_prefix="all"):
        if df.empty:
            st.info("Δεν υπάρχουν εγγραφές για εμφάνιση.")
            return

        for _, row in df.iterrows():
            rid = int(row["id"])
            with st.expander(f"{row['first_name']} {row['last_name']}"):
                # Text inputs
                st.text_input("Επώνυμο", value=row["last_name"] or "", key=f"{tab_prefix}_last_name_{rid}")
                st.text_input("Όνομα", value=row["first_name"] or "", key=f"{tab_prefix}_first_name_{rid}")
                st.text_input("Τηλέφωνο", value=row["phone"] or "", key=f"{tab_prefix}_phone_{rid}")
                st.text_input("Email", value=row["email"] or "", key=f"{tab_prefix}_email_{rid}")

                # Member
                is_member = st.selectbox("Εγγραφή ως μέλος;", ["ΟΧΙ","ΝΑΙ"],
                                         index=0 if row["is_member"]=="ΟΧΙ" else 1,
                                         key=f"{tab_prefix}_is_member_{rid}")
                col1, col2 = st.columns(2)
                with col1:
                    member_month = st.selectbox("Αρχική Εγγραφή - Μήνας", months,
                                                index=months.index(row["member_month"]) if row["member_month"] in months else 0,
                                                key=f"{tab_prefix}_member_month_{rid}")
                with col2:
                    my_val = row["member_year"]
                    try:
                        my_index = years_2000_2050.index(int(my_val)) if (my_val is not None and pd.notna(my_val) and int(my_val) in years_2000_2050) else 0
                    except:
                        my_index = 0
                    member_year = st.selectbox("Αρχική Εγγραφή - Έτος", years_2000_2050,
                                               index=my_index, key=f"{tab_prefix}_member_year_{rid}")
                subscription_year = st.selectbox("Συνδρομή για Έτος", years_2010_2050,
                                                 index=0 if pd.isna(row["subscription_year"]) else years_2010_2050.index(row["subscription_year"]),
                                                 key=f"{tab_prefix}_subscription_year_{rid}")

                # Athlete
                is_athlete = st.selectbox("Είναι Αθλητής;", ["ΟΧΙ","ΝΑΙ"],
                                         index=0 if row["is_athlete"]=="ΟΧΙ" else 1,
                                         key=f"{tab_prefix}_is_athlete_{rid}")
                st.text_input("ΑΜ ΕΟΜ", value=row["eom_number"] or "", key=f"{tab_prefix}_eom_number_{rid}")
                athlete_from_year = st.selectbox("Από Έτος", years_1980_2050,
                                                 index=0 if pd.isna(row["athlete_from_year"]) else years_1980_2050.index(row["athlete_from_year"]),
                                                 key=f"{tab_prefix}_athlete_from_year_{rid}")

                # Save & Delete
                if st.button("💾 Αποθήκευση αλλαγών", key=f"{tab_prefix}_save_{rid}"):
                    run_query("""
                        UPDATE people SET
                            last_name=%s, first_name=%s, phone=%s, email=%s,
                            is_member=%s, member_month=%s, member_year=%s, subscription_year=%s,
                            is_athlete=%s, eom_number=%s, athlete_from_year=%s
                        WHERE id=%s
                    """, (
                        st.session_state[f"{tab_prefix}_last_name_{rid}"],
                        st.session_state[f"{tab_prefix}_first_name_{rid}"],
                        st.session_state[f"{tab_prefix}_phone_{rid}"],
                        st.session_state[f"{tab_prefix}_email_{rid}"],
                        st.session_state[f"{tab_prefix}_is_member_{rid}"],
                        st.session_state[f"{tab_prefix}_member_month_{rid}"],
                        st.session_state[f"{tab_prefix}_member_year_{rid}"],
                        st.session_state[f"{tab_prefix}_subscription_year_{rid}"],
                        st.session_state[f"{tab_prefix}_is_athlete_{rid}"],
                        st.session_state[f"{tab_prefix}_eom_number_{rid}"],
                        st.session_state[f"{tab_prefix}_athlete_from_year_{rid}"],
                        rid
                    ))
                    # Update custom fields
                    custom_attrs = get_member_attributes(rid)
                    for _, attr in custom_attrs.iterrows():
                        save_member_attribute(rid, attr["id"], st.session_state.get(f"{tab_prefix}_{attr['field_name']}_{rid}"))
                    st.success("✅ Οι αλλαγές αποθηκεύτηκαν.")
                    st.rerun()

                if st.button("🗑️ Διαγραφή μέλους", key=f"{tab_prefix}_delete_{rid}"):
                    run_query("DELETE FROM people WHERE id=%s", (rid,))
                    run_query("DELETE FROM member_attributes WHERE member_id=%s", (rid,))
                    st.success("✅ Το μέλος διαγράφηκε.")
                    st.rerun()

    # ---------- Tab6: Editable all entries with enhanced filters and export ----------
    with tab6:
        st.header("📋 Όλα τα Άτομα")

        # Initialize default filter values
        if "filters" not in st.session_state:
            st.session_state.filters = {
                "is_member": "Όλα",
                "is_athlete": "Όλα",
                "is_student": "Όλα",
                "is_interested": "Όλα",
                "member_month": [],
                "member_year": [],
                "subscription_year": [],
                "athlete_from_year": [],
                "student_period_month": [],
                "student_period_year": [],
                "student_university": [],
                "eom_number_search": "",
                "name_search": "",
                "email_search": ""
            }

        f = st.session_state.filters

        with st.expander("🔍 Φίλτρα (προαιρετικά)", expanded=True):
            st.markdown("#### Μέλος")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                f["is_member"] = st.selectbox("Μέλος;", ["Όλα","ΝΑΙ","ΟΧΙ"],
                                              index=["Όλα","ΝΑΙ","ΟΧΙ"].index(f["is_member"]))
            with col2:
                f["member_month"] = st.multiselect("Μήνας Εγγραφής", months, default=f["member_month"])
            with col3:
                f["member_year"] = st.multiselect("Έτος Εγγραφής", years_2000_2050, default=f["member_year"])
            with col4:
                f["subscription_year"] = st.multiselect("Συνδρομή Έτος", years_2010_2050, default=f["subscription_year"])

            st.markdown("#### Αθλητής")
            col5, col6 = st.columns(2)
            with col5:
                f["is_athlete"] = st.selectbox("Αθλητής;", ["Όλα","ΝΑΙ","ΟΧΙ"],
                                               index=["Όλα","ΝΑΙ","ΟΧΙ"].index(f["is_athlete"]))
            with col6:
                f["athlete_from_year"] = st.multiselect("Από Έτος Αθλητή", years_1980_2050, default=f["athlete_from_year"])
            f["eom_number_search"] = st.text_input("Αναζήτηση ΑΜ ΕΟΜ", value=f["eom_number_search"])

            st.markdown("#### Μαθητής")
            col7, col8, col9 = st.columns(3)
            with col7:
                f["is_student"] = st.selectbox("Μαθητής;", ["Όλα","ΝΑΙ","ΟΧΙ"],
                                               index=["Όλα","ΝΑΙ","ΟΧΙ"].index(f["is_student"]))
            with col8:
                f["student_period_month"] = st.multiselect("Μήνας Μαθητή", months, default=f["student_period_month"])
            with col9:
                f["student_period_year"] = st.multiselect("Έτος Μαθητή", years_2010_2050, default=f["student_period_year"])
            f["student_university"] = st.multiselect("Πανεπιστήμιο;", ["ΟΧΙ","ΝΑΙ"], default=f["student_university"])

            st.markdown("#### Ενδιαφερόμενος")
            col10 = st.columns(1)
            f["is_interested"] = st.selectbox("Ενδιαφερόμενος;", ["Όλα","ΝΑΙ","ΟΧΙ"],
                                              index=["Όλα","ΝΑΙ","ΟΧΙ"].index(f["is_interested"]))

            st.markdown("#### Γενική Αναζήτηση")
            f["name_search"] = st.text_input("Αναζήτηση (Όνομα/Επώνυμο)", value=f["name_search"])
            f["email_search"] = st.text_input("Αναζήτηση (Email)", value=f["email_search"])

            if st.button("♻️ Reset Filters"):
                for k in f.keys():
                    if isinstance(f[k], list):
                        f[k] = []
                    elif isinstance(f[k], str):
                        f[k] = "" if "search" in k or k=="student_university" else "Όλα"
                st.rerun()

        # Apply filters to df
        filtered_df = df_all.copy()

        # Single-choice filters
        for col in ["is_member","is_athlete","is_student","is_interested"]:
            if f[col] != "Όλα":
                filtered_df = filtered_df[filtered_df[col]==f[col]]

        # Multi-choice filters
        multi_filters = [
            ("member_month","member_month"), ("member_year","member_year"),
            ("subscription_year","subscription_year"), ("athlete_from_year","athlete_from_year"),
            ("student_period_month","student_period_month"), ("student_period_year","student_period_year"),
            ("student_university","student_university")
        ]
        for key, col_name in multi_filters:
            if f[key]:
                filtered_df = filtered_df[filtered_df[col_name].isin(f[key])]

        # Text search
        if f["name_search"]:
            ns = f["name_search"].strip().lower()
            filtered_df = filtered_df[
                filtered_df["first_name"].str.lower().str.contains(ns) |
                filtered_df["last_name"].str.lower().str.contains(ns)
            ]

        if f["eom_number_search"]:
            eom_s = f["eom_number_search"].strip()
            filtered_df = filtered_df[filtered_df["eom_number"].astype(str).str.contains(eom_s, na=False)]

        if f["email_search"]:
            email_s = f["email_search"].strip()
            filtered_df = filtered_df[filtered_df["email"].astype(str).str.contains(email_s, na=False)]

        st.success(f"Βρέθηκαν {len(filtered_df)} εγγραφές.")

        col_export1, col_export2 = st.columns(2)
        with col_export1:
            if not filtered_df.empty:
                excel_filtered = excel_bytes_from_df(filtered_df, sheet_name="Φιλτραρισμένα")
                st.download_button(
                    label="📊 Λήψη Φιλτραρισμένων Δεδομένων",
                    data=excel_filtered,
                    file_name=generate_excel_filename("filtered_data"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        with col_export2:
            if not df_all.empty:
                excel_all = excel_bytes_from_df(df_all, sheet_name="Όλα")
                st.download_button(
                    label="📊 Λήψη Όλων των Δεδομένων",
                    data=excel_all,
                    file_name=generate_excel_filename("all_data"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        display_editable_all(filtered_df, tab_prefix="all")

    # ---------- Tab7: Settings ----------
    with tab7:
        st.header("⚙️ Ρυθμίσεις")
        new_name = st.text_input("Αλλαγή ονόματος ομίλου", value=club_name, key="settings_club_name")
        if st.button("💾 Αποθήκευση αλλαγής"):
            set_club_name(new_name.strip())
            st.success("Το όνομα ενημερώθηκε! Επανεκκινήστε την εφαρμογή.")
            st.rerun()

    # ---------- Tab8: Excel Import ----------
    with tab8:
        st.header("📥 Εισαγωγή δεδομένων από Excel")
        uploaded_file = st.file_uploader("Επιλέξτε αρχείο Excel", type=["xlsx"])
        if uploaded_file:
            xl_file = pd.ExcelFile(uploaded_file)
            sheet_names = xl_file.sheet_names
            
            selected_sheet = st.selectbox("Επιλέξτε φύλλο εργασίας:", sheet_names)
            df_import = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            
            st.markdown("### Επιλέξτε αντιστοίχιση στηλών")
            
            key_fields = {}
            st.markdown("#### Βασικά Πεδία")
            for field in ["first_name", "last_name", "phone", "email", "is_member", "is_athlete", "eom_number"]:
                options = ["none"] + list(df_import.columns)
                sel = st.selectbox(f"{field.replace('_',' ').capitalize()}:", options, key=f"map_{field}")
                if sel != "none":
                    key_fields[field] = sel

            st.markdown("#### Προσαρμοσμένα Πεδία")
            custom_fields = get_custom_fields()
            custom_fields_mapping = {}
            if not custom_fields.empty:
                st.info("Επιλέξτε τις στήλες από το Excel που αντιστοιχούν στα προσαρμοσμένα πεδία:")
                for _, field in custom_fields.iterrows():
                    options = ["none"] + list(df_import.columns)
                    sel = st.selectbox(
                        f"{field['field_name']} (Κατηγορίες: {field['applicable_domains']}):",
                        options, 
                        key=f"map_custom_{field['field_name']}"
                    )
                    if sel != "none":
                        custom_fields_mapping[field['id']] = {
                            "field_name": field['field_name'],
                            "excel_column": sel
                        }
            else:
                st.info("Δεν υπάρχουν προσαρμοσμένα πεδία. Δημιουργήστε κάποια στην κατηγορία 'Διαχείριση Πεδίων'.")

            if st.button("📥 Εισαγωγή επιλεγμένων στηλών"):
                existing = fetch_df("SELECT first_name,last_name,email FROM people")
                inserted, skipped = 0, 0
                
                for _, row in df_import.iterrows():
                    data = {k: row[v] for k, v in key_fields.items()}
                    
                    # Skip if duplicate
                    if ((existing["first_name"].astype(str).str.lower() == str(data.get("first_name", "")).lower()) &
                        (existing["last_name"].astype(str).str.lower() == str(data.get("last_name", "")).lower()) &
                        (existing["email"].astype(str).str.lower() == str(data.get("email", "")).lower())).any():
                        skipped += 1
                        continue
                    
                    run_query("""
                        INSERT INTO people (first_name, last_name, phone, email, is_member, is_athlete, eom_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data.get("first_name"),
                        data.get("last_name"),
                        data.get("phone"),
                        data.get("email"),
                        data.get("is_member"),
                        data.get("is_athlete"),
                        data.get("eom_number")
                    ))
                    
                    member_result = fetch_df(
                        "SELECT id FROM people WHERE email=%s AND first_name=%s AND last_name=%s",
                        (data.get("email"), data.get("first_name"), data.get("last_name"))
                    )
                    if member_result.empty:
                        continue
                    member_id = member_result["id"].iloc[0]
                    
                    for field_id, field_info in custom_fields_mapping.items():
                        try:
                            field_value = str(row[field_info['excel_column']])
                            if field_value and field_value.lower() != "nan":
                                save_member_attribute(member_id, field_id, field_value)
                        except Exception as e:
                            st.warning(f"⚠️ Σφάλμα κατά την εισαγωγή του {field_info['field_name']} για {data.get('first_name')}: {str(e)}")
                    
                    inserted += 1
                
                st.success(f"✅ Εισήχθησαν {inserted} νέα μέλη.")
                if skipped > 0:
                    st.warning(f"⚠️ Παράκαμψη {skipped} διπλότυπων εγγραφών.")
                st.rerun()

    # ---------- Tab9: Custom Fields Management ----------
    with tab9:
        st.header("⚙️ Διαχείριση Πεδίων")
        custom_fields = get_custom_fields()
        if custom_fields.empty:
            st.info("Δεν υπάρχουν προσαρμοσμένα πεδία.")
        else:
            for _, field in custom_fields.iterrows():
                st.markdown(f"### {field['field_name']}")
                st.write(f"**Εφαρμόσιμες Κατηγορίες:** {field['applicable_domains']}")
                if st.button(f"🗑️ Διαγραφή '{field['field_name']}'", key=f"delete_{field['id']}"):
                    delete_custom_field(field["id"])
                    st.success(f"✅ Το πεδίο '{field['field_name']}' διαγράφηκε.")
                    st.rerun()

        st.markdown("### ➕ Προσθήκη Νέου Πεδίου")
        new_field_name = st.text_input("Όνομα Πεδίου (π.χ. ΑΜΚΑ)", key="new_field_name", help="Αυτό το όνομα θα εμφανίζεται στα πεδία μελών")
        new_applicable_domains = st.multiselect(
            "Σε ποιες κατηγορίες μελών θα εμφανίζεται;",
            ["ΓΕΝΙΚΑ ΣΤΟΙΧΕΙΑ", "ΜΕΛΟΣ", "ΑΘΛΗΤΗΣ", "ΜΑΘΗΤΗΣ", "ΕΝΔΙΑΦΕΡΟΜΕΝΟΣ"],
            key="new_applicable_domains"
        )
        if st.button("➕ Προσθήκη Πεδίου"):
            if not new_field_name:
                st.warning("⚠️ Συμπληρώστε το Όνομα Πεδίου.")
            elif not new_applicable_domains:
                st.warning("⚠️ Επιλέξτε τουλάχιστον μία κατηγορία μελών.")
            else:
                add_custom_field(new_field_name.strip(), new_field_name.strip(), new_applicable_domains)
                st.success(f"✅ Το πεδίο '{new_field_name}' προστέθηκε.")
                st.rerun()
