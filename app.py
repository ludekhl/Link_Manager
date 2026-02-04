import streamlit as st
import sqlite3
import os
import pandas as pd

# --- Database Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'links_db.sqlite')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS groups 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  url TEXT, 
                  group_name TEXT,
                  FOREIGN KEY(group_name) REFERENCES groups(name))''')
    c.execute("INSERT OR IGNORE INTO groups (name) VALUES ('General')")
    conn.commit()
    conn.close()

def add_group(name):
    if not name: return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        st.error("Group already exists!")
    conn.close()

def rename_group(old_name, new_name):
    if not new_name or old_name == "General": return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Update the group name itself
        c.execute("UPDATE groups SET name = ? WHERE name = ?", (new_name, old_name))
        # Update all links associated with this group
        c.execute("UPDATE links SET group_name = ? WHERE group_name = ?", (new_name, old_name))
        conn.commit()
    except sqlite3.IntegrityError:
        st.error("The new group name is already taken.")
    conn.close()

def delete_group(group_name):
    if group_name == "General":
        st.error("Cannot delete the General group.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Move links to General before deleting group
    c.execute("UPDATE links SET group_name = 'General' WHERE group_name = ?", (group_name,))
    c.execute("DELETE FROM groups WHERE name = ?", (group_name,))
    conn.commit()
    conn.close()

def add_link(name, url, group):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO links (name, url, group_name) VALUES (?, ?, ?)", (name, url, group))
    conn.commit()
    conn.close()

def update_link(link_id, name, url, group):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE links SET name=?, url=?, group_name=? WHERE id=?", (name, url, group, link_id))
    conn.commit()
    conn.close()

def delete_links(ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany("DELETE FROM links WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def get_all_groups():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM groups")
    groups = [row[0] for row in c.fetchall()]
    conn.close()
    return groups

def get_links_df(search_query=""):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id, name, url, group_name FROM links"
    df = pd.read_sql_query(query, conn)
    conn.close()
    if search_query:
        mask = df['name'].str.contains(search_query, case=False) | df['url'].str.contains(search_query, case=False)
        df = df[mask]
    return df

# --- UI Logic ---
st.set_page_config(page_title="Link Manager", layout="wide")
init_db()

# Handle Bookmarklet params
query_params = st.query_params
initial_url = query_params.get("url", "")
initial_name = query_params.get("name", "")

st.title("🔗 Link Database")

# --- Sidebar ---
with st.sidebar:
    st.header("Actions")
    
    # 1. Add New Link
    with st.expander("➕ Add New Link", expanded=bool(initial_url)):
        l_name = st.text_input("Name", value=initial_name)
        l_url = st.text_input("URL", value=initial_url)
        groups = get_all_groups()
        l_group = st.selectbox("Group", options=groups)
        if st.button("Save Link", use_container_width=True):
            if l_name and l_url:
                add_link(l_name, l_url, l_group)
                st.query_params.clear()
                st.rerun()

    # 2. Manage Groups
    with st.expander("📁 Manage Groups"):
        # Create
        new_g = st.text_input("New Group Name")
        if st.button("Add Group", use_container_width=True):
            add_group(new_g)
            st.rerun()
        
        st.divider()
        
        # Rename/Delete
        current_groups = [g for g in get_all_groups() if g != "General"]
        if current_groups:
            target_g = st.selectbox("Select Group to Edit", options=current_groups)
            rename_val = st.text_input("Rename to", value=target_g)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update", use_container_width=True):
                    rename_group(target_g, rename_val)
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_group(target_g)
                    st.rerun()
        else:
            st.caption("No custom groups to edit.")

# --- Main Dashboard ---
search = st.text_input("🔍 Quick Search", placeholder="Filter by name or domain...")
df = get_links_df(search)

if df.empty:
    st.info("No links found.")
else:
    st.subheader("All Links")
    
    column_config = {
        "id": None,
        "url": st.column_config.LinkColumn("URL", width="medium"),
        "name": st.column_config.TextColumn("Display Name", width="medium"),
        "group_name": st.column_config.SelectboxColumn("Group", options=get_all_groups(), width="small")
    }

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key="link_editor",
        num_rows="dynamic"
    )

    if st.button("💾 Save Table Changes"):
        for index, row in edited_df.iterrows():
            update_link(row['id'], row['name'], row['url'], row['group_name'])
        st.success("Changes synced!")
        st.rerun()

    st.divider()
    with st.expander("🗑️ Bulk Delete Links"):
        to_delete = st.multiselect("Select links to remove", 
                                   options=df['id'].tolist(),
                                   format_func=lambda x: df.loc[df['id']==x, 'name'].values[0])
        if st.button("Confirm Delete", type="primary"):
            delete_links(to_delete)
            st.rerun()