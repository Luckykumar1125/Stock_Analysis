import os
import json
import sqlite3
import math
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple
from io import BytesIO
from pathlib import Path
import requests
from matplotlib import pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg')
from core.schemas import Transaction

# -------------------------
# Deterministic rules
# -------------------------
DETERMINISTIC_MAP = {
    "Food & Dining": ["SWIGGY", "ZOMATO", "KFC", "MCDONALD", "PIZZA", "DOMINOS"],
    "Shopping": ["AMAZON", "FLIPKART", "MEESHO"],
    "Online Subscriptions": ["NETFLIX", "SPOTIFY", "AMAZON PRIME", "HOTSTAR", "DISNEY+"],
    "Salary": ["SALARY", "PAYROLL"],
    "Bills & Utilities": ["ELECTRICITY", "AIRTEL", "JIO", "WATER BILL", "BILL"],
    "Travel": ["OLA", "UBER", "IRCTC", "GOIBIBO", "MAHANAGAR", "INDIGO", "SPICEJET"],
    "Entertainment": ["CINEMA", "BOOKMYSHOW", "MOVIE", "THEATRE"]
}

DEFAULT_CATEGORY = "Others" 

# Define keywords for transaction classification
EXPENSE_KEYWORDS = ["debit", "paid", "withdraw", "purchase", "spent", "transfer out"]
INCOME_KEYWORDS = ["credit", "received", "deposit", "salary", "transfer in"]


# -------------------------
# DB reading helpers
# -------------------------
def open_db(db_path: str) -> sqlite3.Connection:
    """Opens a SQLite database connection using an absolute path."""
    # 1. Get the absolute path of the directory containing THIS file
    script_dir = Path(__file__).resolve().parent

    # 2. Navigate up to the 'backend' folder (assuming standard project structure)
    backend_dir = script_dir.parent.parent 

    # 3. Construct the final absolute path to the database file
    DB_FILE_PATH = backend_dir / "bank_statements.db"
    
    print(f"Attempting to connect to absolute path: {DB_FILE_PATH}")

    # 4. Connect using the absolute path
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def read_transactions_from_db(db_path: str) -> List[Transaction]:
    """
    Reads transactions from the 'transactions' table or tries to parse a JSON column.
    """
    conn = open_db("backend/bank_statements.db")
    cur = conn.cursor()

    # 1) Try reading rows from transactions table
    try:
        cur.execute("SELECT date, time, transaction_type, name, amount FROM transactions")
        rows = cur.fetchall()
        if rows:
            txs = []
            for r in rows:
                txs.append(Transaction(
                    date=str(r["date"]),
                    time=str(r["time"]) if r["time"] is not None else None,
                    transaction_type=str(r["transaction_type"]) if r["transaction_type"] is not None else "",
                    name=str(r["name"]) if r["name"] is not None else "",
                    amount=float(r["amount"]) if r["amount"] is not None else 0.0
                ))
            conn.close()
            return txs
    except sqlite3.OperationalError:
        pass # table doesn't exist; fall through

    # 2) Try reading from a table that has a JSON column (original complex logic preserved)
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            cur.execute(f"PRAGMA table_info('{t}')")
            cols = [c[1] for c in cur.fetchall()]
            for col in cols:
                try:
                    cur.execute(f"SELECT {col} FROM {t} LIMIT 1")
                    row = cur.fetchone()
                    if row and row[0]:
                        text = row[0]
                        if isinstance(text, str) and text.strip().startswith("["):
                            parsed = json.loads(text)
                            if isinstance(parsed, list):
                                txs = []
                                for item in parsed:
                                    txs.append(Transaction(
                                        date=str(item.get("date", "")),
                                        time=item.get("time"),
                                        transaction_type=item.get("transaction_type", ""),
                                        name=item.get("name", ""),
                                        amount=float(item.get("amount", 0.0))
                                    ))
                                conn.close()
                                return txs
                except Exception:
                    continue
    except Exception:
        pass

    conn.close()
    return []

# -------------------------
# Deterministic classifier
# -------------------------
def categorize_deterministic(name: str) -> str:
    """Categorizes a transaction name based on a predefined map."""
    if not name:
        return DEFAULT_CATEGORY
    n = name.upper()
    for category, tokens in DETERMINISTIC_MAP.items():
        for token in tokens:
            if token in n:
                return category
    return None

# -------------------------
# Groq LLM classifier (fallback)
# -------------------------
def classify_with_llm(name: str) -> str:
    """
    Calls a Groq LLM completion endpoint to classify the merchant name into a category.
    Uses an improved, more directive prompt for better classification accuracy.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return DEFAULT_CATEGORY

    categories = list(DETERMINISTIC_MAP.keys())
    
    # Define detailed category descriptions for the LLM
    category_definitions = {
        "Food & Dining": "Restaurants, cafes, food delivery (Swiggy, Zomato, etc.).",
        "Shopping": "General retail purchases, e-commerce (Amazon, Flipkart, Meesho, etc.).",
        "Online Subscriptions": "Recurring digital services (Netflix, Spotify, Prime, etc.).",
        "Salary": "Income or payroll deposits.",
        "Bills & Utilities": "Monthly payments for electricity, water, phone, internet.",
        "Travel": "Taxi rides (Uber, Ola), airlines, rail, hotels, public transport.",
        "Entertainment": "Movies, concerts, theatre, gaming, events (BookMyShow, cinema).",
        "Others": "Any transaction that does not clearly fit into the defined categories."
    }

    # Format the definitions block for the prompt
    definitions_block = "\n".join([f"- **{k}**: {v}" for k, v in category_definitions.items()])

    # --- THE IMPROVED PROMPT ---
    prompt = (
        "SYSTEM INSTRUCTION: You are a strict categorization assistant for personal finance transactions. "
        "Your task is to analyze the provided merchant name and return the BEST-MATCHING category "
        "from the list below. YOU MUST RETURN ONLY THE CATEGORY NAME and NOTHING ELSE.\n\n"
        
        "CATEGORY DEFINITIONS:\n"
        f"{definitions_block}\n\n"
        
        f"MERCHANT NAME TO CLASSIFY: \"{name}\"\n"
        "OUTPUT (Category Name ONLY):"
    )

    url = "https://api.groq.ai/v1/complete"
    payload = {
        # Consider a better general-purpose model like Llama 3 8B if available, 
        # but retaining the current model as per your original code:
        "model": "meta-llama/llama-guard-4-12b",
        "prompt": prompt,
        "max_tokens": 10, # Increased slightly to accommodate longer category names
        "temperature": 0.0, # Keep at 0.0 for reliable classification
        "stop": ["\n"]
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # ... (Rest of the API call logic remains the same)
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()
        
        text = None
        if isinstance(data, dict):
            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0].get("text") or data["choices"][0].get("message", {}).get("content")
            elif "completion" in data:
                text = data["completion"]
            elif "text" in data:
                text = data["text"]
        
        if text:
            # Clean up the output string
            candidate = text.strip().strip('"').strip().title()
            
            # Check if the candidate matches any known category exactly
            known_categories = list(category_definitions.keys())
            if candidate in known_categories:
                return candidate
            
            # Fallback check (less strict matching)
            for cat in known_categories:
                if cat.upper() in candidate.upper():
                    return cat

            # If the model returns a valid, capitalized answer that is not a defined category
            # we return "Others" to maintain the integrity of the defined categories.
            return DEFAULT_CATEGORY
    
    except Exception:
        return DEFAULT_CATEGORY

    return DEFAULT_CATEGORY

# -------------------------
# Full categorization pipeline
# -------------------------
def categorize_transactions(transactions: List[Transaction], use_llm_fallback: bool = True) -> List[Dict[str, Any]]:
    """Runs transactions through deterministic and optional LLM classification."""
    categorized = []
    for t in transactions:
        cat = categorize_deterministic(t.name)
        used_llm = False
        if not cat and use_llm_fallback:
            cat = classify_with_llm(t.name)
            used_llm = True
        if not cat:
            cat = DEFAULT_CATEGORY
        categorized.append({
            "date": t.date,
            "time": t.time,
            "transaction_type": t.transaction_type,
            "name": t.name,
            "amount": t.amount,
            "category": cat,
            "llm_used": used_llm
        })
    return categorized

# -------------------------
# Analytics
# -------------------------
def monthly_spend_summary(categorized_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates summary statistics for transactions."""
    total_received = 0.0
    total_spent = 0.0
    per_category = defaultdict(float)
    merchant_counter = Counter()
    amounts = []

    for tx in categorized_transactions:
        amt = float(tx["amount"])
        amounts.append(amt)
        name = tx.get("name", "").strip() or "Unknown"
        merchant_counter[name] += 1
        cat = tx.get("category", DEFAULT_CATEGORY)
        typ = (tx.get("transaction_type") or "").lower()

        is_income = any(k in typ for k in INCOME_KEYWORDS) or cat == "Salary"
        is_expense = any(k in typ for k in EXPENSE_KEYWORDS) and cat != "Salary"
        
        # Use an amount's sign as a final tie-breaker if type is ambiguous
        if is_income or (not is_expense and amt > 0):
            total_received += amt
            # Only track amount per category for expenses (for plotting a spend pie chart)
            if cat == "Salary":
                per_category[cat] += amt # Optionally track income category amounts
        elif is_expense or (not is_income and amt < 0):
            total_spent += abs(amt) # Ensure total spent is positive
            per_category[cat] += abs(amt)

    net_savings = total_received - total_spent
    tx_count = len(categorized_transactions)
    # Average calculation includes all transactions (both income and expense)
    avg_tx = (sum(amounts) / tx_count) if tx_count > 0 else 0.0

    top_merchants = merchant_counter.most_common(5)
    top_merchants_list = [{"merchant": m, "count": c} for m, c in top_merchants]

    # Filter out Salary from the general category amounts if it skews the spend plot
    # A pie chart of spending typically excludes income categories.
    spend_per_category = {
        k: v for k, v in per_category.items() if k != "Salary" and v > 0
    }

    return {
        "total_received": round(total_received, 2),
        "total_spent": round(total_spent, 2),
        "net_savings": round(net_savings, 2),
        "top_merchants": top_merchants_list,
        "transaction_count": tx_count,
        "average_transaction_size": round(avg_tx, 2),
        "amount_per_category": {k: round(v, 2) for k, v in spend_per_category.items()},
    }

# -------------------------
# Charts (matplotlib)
# -------------------------
# -------------------------
# Charts (Modern Dark Mode)
# -------------------------

# A palette that pops against dark backgrounds (Blue, Teal, Purple, Amber, Emerald)
DARK_MODE_PALETTE = ["#3b82f6", "#14b8a6", "#8b5cf6", "#f59e0b", "#10b981", "#ec4899", "#06b6d4"]

def pie_chart_category(amount_per_category: Dict[str, float]) -> bytes:
    """
    Returns PNG bytes for a modern Dark Mode Donut Chart.
    """
    # 1. Filter Data (Ignore zero or negative spend)
    data = {k: v for k, v in amount_per_category.items() if v > 0.01}
    
    if not data:
         fig, ax = plt.subplots(figsize=(1, 1))
         fig.patch.set_alpha(0.0) # Transparent
         ax.axis('off')
         buf = BytesIO()
         plt.savefig(buf, format='png', transparent=True)
         plt.close(fig)
         buf.seek(0)
         return buf.read()

    # 2. Sort Data (Largest slice starts at 12 o'clock)
    labels = list(data.keys())
    values = list(data.values())
    
    sorted_indices = np.argsort(values)[::-1]
    sorted_labels = [labels[i] for i in sorted_indices]
    sorted_values = [values[i] for i in sorted_indices]

    # 3. Prepare Colors
    colors = DARK_MODE_PALETTE * (len(sorted_labels) // len(DARK_MODE_PALETTE) + 1)
    colors = colors[:len(sorted_labels)]

    # 4. Setup Plot
    fig, ax = plt.subplots(figsize=(7, 7))
    fig.patch.set_alpha(0.0) # Transparent background
    ax.patch.set_alpha(0.0)

    # 5. Helper to hide labels on tiny slices (< 3%)
    def make_autopct(val_list):
        def my_autopct(pct):
            return f'{pct:.0f}%' if pct > 3 else ''
        return my_autopct

    # 6. Draw Donut
    wedges, texts, autotexts = ax.pie(
        sorted_values,
        labels=sorted_labels,
        colors=colors,
        autopct=make_autopct(sorted_values),
        startangle=90,
        counterclock=False,
        pctdistance=0.80,
        labeldistance=1.25, rotatelabels=True,
        wedgeprops={'width': 0.5, 'edgecolor': '#1e293b', 'linewidth': 2},
        textprops={'color': 'white', 'fontsize': 14, 'fontweight': 'bold'}
    )

    # Style internal percentages
    plt.setp(autotexts, size=9, weight="bold", color="white")
    
    # Style external labels (optional: make them slightly grey to reduce visual noise)
    plt.setp(texts, color="#e2e8f0") 

    ax.axis('equal')
    
    buf = BytesIO()
    # transparent=True is critical for the glassmorphism look
    plt.savefig(buf, format="png", bbox_inches='tight', transparent=True, dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

def bar_chart_top_merchants(categorized_transactions: List[Dict[str, Any]], top_n: int = 5) -> bytes:
    """
    Returns PNG bytes for a Dark Mode Horizontal Bar Chart.
    """
    # Calculate net spend per merchant
    merchant_amounts = defaultdict(float)
    for tx in categorized_transactions:
        amt = float(tx.get("amount", 0.0))
        cat = tx.get("category", "Others")
        typ = (tx.get("transaction_type") or "").lower()
        
        # Logic: If it's an expense, add to total
        is_expense = any(k in typ for k in EXPENSE_KEYWORDS) and cat != "Salary"
        if is_expense:
            merchant_amounts[tx.get("name", "Unknown")] += abs(amt)
        elif amt > 0 and cat != "Salary" and not any(k in typ for k in INCOME_KEYWORDS):
            # Fallback for positive amounts that are expenses
            merchant_amounts[tx.get("name", "Unknown")] += amt

    # Sort top N
    top = sorted(merchant_amounts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    names = [t[0] for t in top]
    amounts = [t[1] for t in top]

    # Setup Plot
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_alpha(0.0) # Transparent
    ax.patch.set_alpha(0.0)
    
    if not amounts:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis('off')
    else:
        # Horizontal bars
        y_pos = np.arange(len(names))
        # Reverse order so biggest is at top
        ax.barh(y_pos[::-1], amounts[::-1], color='#3b82f6', height=0.6) 
        
        # Labels and Ticks styling for Dark Mode
        ax.set_yticks(y_pos[::-1])
        ax.set_yticklabels(names[::-1], color='white', fontsize=10)
        ax.set_xlabel("Amount Spent (₹)", color='#94a3b8')
        ax.tick_params(axis='x', colors='#94a3b8')
        ax.tick_params(axis='y', colors='white')
        
        # Remove ugly borders (spines)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#334155')
        ax.spines['left'].set_visible(False)

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf.read()