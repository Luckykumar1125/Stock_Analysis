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
import concurrent.futures
import re
matplotlib.use('Agg')
from core.schemas import Transaction

# -------------------------
# Configuration
# -------------------------
CACHE_FILE = "merchant_category_cache.json"
MAX_WORKERS = 10  # Number of simultaneous API calls

# -------------------------
# Deterministic rules
# -------------------------
DETERMINISTIC_MAP = {
    "Food & Dining": ["SWIGGY", "ZOMATO", "KFC", "MCDONALD", "PIZZA", "DOMINOS", "RESTAURANT", "CAFE"],
    "Shopping": ["AMAZON", "FLIPKART", "MEESHO", "MYNTRA", "AJIO", "RELIANCE RETAIL"],
    "Online Subscriptions": ["NETFLIX", "SPOTIFY", "AMAZON PRIME", "HOTSTAR", "DISNEY+", "YOUTUBE", "APPLE"],
    "Salary": ["SALARY", "PAYROLL", "CREDIT INTEREST"],
    "Bills & Utilities": ["ELECTRICITY", "AIRTEL", "JIO", "WATER BILL", "BILL", "BESCOM", "GAS"],
    "Travel": ["OLA", "UBER", "IRCTC", "GOIBIBO", "MAHANAGAR", "INDIGO", "SPICEJET", "METRO", "RAPIDO"],
    "Entertainment": ["CINEMA", "BOOKMYSHOW", "MOVIE", "THEATRE", "PVR", "INOX"]
}

DEFAULT_CATEGORY = "Others" 
EXPENSE_KEYWORDS = ["debit", "paid", "withdraw", "purchase", "spent", "transfer out"]
INCOME_KEYWORDS = ["credit", "received", "deposit", "salary", "transfer in"]

# -------------------------
# Caching Helpers
# -------------------------
def load_cache() -> Dict[str, str]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache: Dict[str, str]):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except:
        pass

# -------------------------
# DB reading helpers
# -------------------------
# -------------------------
# DB reading helpers (FIXED)
# -------------------------
def open_db(db_path: str) -> sqlite3.Connection:
    # FIX: Use the db_path passed to the function, do not ignore it!
    if not db_path:
        raise ValueError("Database path cannot be empty")
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def read_transactions_from_db(db_path: str) -> List[Transaction]:
    # FIX: Pass the actual db_path to open_db
    conn = open_db(db_path) 
    cur = conn.cursor()
    txs = []

    # 1) Try standard table
    try:
        cur.execute("SELECT date, time, transaction_type, name, amount FROM transactions")
        rows = cur.fetchall()
        if rows:
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
        pass 

    # 2) Fallback: JSON column scan
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
# Classification Logic
# -------------------------
def categorize_deterministic(name: str) -> str:
    if not name:
        return DEFAULT_CATEGORY
    n = name.upper()
    for category, tokens in DETERMINISTIC_MAP.items():
        for token in tokens:
            if token in n:
                return category
    return None

def classify_with_llm(name: str) -> str:
    """Classifies a SINGLE merchant name. Exception safe."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return DEFAULT_CATEGORY

    # Shorter prompt to save tokens and latency
    prompt = (
        "Classify this merchant into: Food & Dining, Shopping, Online Subscriptions, "
        "Salary, Bills & Utilities, Travel, Entertainment, or Others.\n"
        "Return ONLY the category name.\n\n"
        f"Merchant: \"{name}\"\n"
        "Category:"
    )

    url = "https://api.groq.ai/v1/complete"
    payload = {
        "model": "meta-llama/llama-guard-4-12b", # Consider switching to llama3-8b-8192 for speed if available
        "prompt": prompt,
        "max_tokens": 15,
        "temperature": 0.0,
        "stop": ["\n"]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5) # 5s timeout
        r.raise_for_status()
        data = r.json()
        
        text = None
        if "choices" in data and len(data["choices"]) > 0:
            text = data["choices"][0].get("text")
        
        if text:
            clean_text = text.strip().strip('"').title()
            # Basic validation
            valid_cats = list(DETERMINISTIC_MAP.keys()) + ["Others"]
            for vc in valid_cats:
                if vc in clean_text:
                    return vc
            return "Others"
    except Exception:
        pass
    
    return DEFAULT_CATEGORY

# -------------------------
# Optimized Pipeline
# -------------------------
def categorize_transactions(transactions: List[Transaction], use_llm_fallback: bool = True) -> List[Dict[str, Any]]:
    categorized_results = []
    
    # 1. Load Cache
    cache = load_cache()
    original_cache_size = len(cache)
    
    # 2. Identify unique unknown merchants
    unknown_merchants = set()
    temp_results = [] # To store intermediate state (index, Transaction, category)

    for i, t in enumerate(transactions):
        # Try deterministic first
        cat = categorize_deterministic(t.name)
        
        # If deterministic failed, check cache
        if not cat and t.name in cache:
            cat = cache[t.name]
            
        # If still unknown and we want to use LLM, mark for batch processing
        if not cat and use_llm_fallback and t.name:
            unknown_merchants.add(t.name)
            cat = None # Placeholder
            
        if not cat and not use_llm_fallback:
            cat = DEFAULT_CATEGORY

        temp_results.append({"tx": t, "cat": cat})

    # 3. Process unknown merchants in Parallel
    new_categories = {}
    if unknown_merchants:
        print(f"Fetching categories for {len(unknown_merchants)} unique merchants via LLM...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_merchant = {executor.submit(classify_with_llm, m): m for m in unknown_merchants}
            
            for future in concurrent.futures.as_completed(future_to_merchant):
                merchant = future_to_merchant[future]
                try:
                    res = future.result()
                    new_categories[merchant] = res
                    cache[merchant] = res # Update cache in memory
                except Exception:
                    new_categories[merchant] = DEFAULT_CATEGORY

    # 4. Save Cache if updated
    if len(cache) > original_cache_size:
        save_cache(cache)

    # helper: normalize amount sign based on transaction_type / category
    def _signed_amount(amt, typ, cat):
        try:
            a = float(amt)
        except Exception:
            a = 0.0

        typ = (typ or "").lower()
        # if explicit expense keyword present -> treat as money out
        if any(k in typ for k in EXPENSE_KEYWORDS):
            return -abs(a)
        # if explicit income keyword or Salary category -> treat as money in
        if any(k in typ for k in INCOME_KEYWORDS) or cat == "Salary":
            return abs(a)
        # else preserve sign if negative, else keep positive (best-effort)
        return a

    # 5. Assemble Final List
    for item in temp_results:
        t = item["tx"]
        cat = item["cat"]
        
        # If it was waiting for LLM, get it from the new batch
        llm_used_flag = False
        if cat is None:
            cat = new_categories.get(t.name, DEFAULT_CATEGORY)
            llm_used_flag = True if t.name in new_categories else False
            
        signed_amt = _signed_amount(t.amount, t.transaction_type, cat)

        categorized_results.append({
            "date": t.date,
            "time": t.time,
            "transaction_type": t.transaction_type,
            "name": t.name,
            "amount": float(t.amount) if t.amount is not None else 0.0,   # original raw amount
            "signed_amount": signed_amt,                                  # normalized sign-aware amount
            "category": cat,
            "llm_used": llm_used_flag
        })

    return categorized_results


# -------------------------
# Analytics (Unchanged)
# -------------------------
def monthly_spend_summary(categorized_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_received = 0.0
    total_spent = 0.0
    per_category = defaultdict(float)
    merchant_counter = Counter()
    amounts = []

    for tx in categorized_transactions:
        # prefer signed_amount if present
        amt = tx.get("signed_amount", None)
        if amt is None:
            try:
                amt = float(tx.get("amount", 0.0))
            except Exception:
                amt = 0.0

        amounts.append(abs(amt))  # for averages we use absolute transaction size
        name = tx.get("name", "").strip() or "Unknown"
        merchant_counter[name] += 1
        cat = tx.get("category", DEFAULT_CATEGORY)
        typ = (tx.get("transaction_type") or "").lower()

        # sign-aware accounting: positive = money in, negative = money out
        if amt >= 0:
            total_received += amt
        else:
            total_spent += abs(amt)
            if cat != "Salary":  # don't count Salary as an expense category
                per_category[cat] += abs(amt)

    net_savings = total_received - total_spent
    tx_count = len(categorized_transactions)
    avg_tx = (sum(amounts) / tx_count) if tx_count > 0 else 0.0

    top_merchants = merchant_counter.most_common(5)
    top_merchants_list = [{"merchant": m, "count": c} for m, c in top_merchants]
    spend_per_category = {k: v for k, v in per_category.items() if k != "Salary" and v > 0}

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
# Charts (Modern Dark Mode) - Unchanged
# -------------------------
DARK_MODE_PALETTE = ["#3b82f6", "#14b8a6", "#8b5cf6", "#f59e0b", "#10b981", "#ec4899", "#06b6d4"]

def pie_chart_category(amount_per_category: Dict[str, float]) -> bytes:
    data = {k: v for k, v in amount_per_category.items() if v > 0.01}
    if not data:
         fig, ax = plt.subplots(figsize=(1, 1)); fig.patch.set_alpha(0.0); ax.axis('off')
         buf = BytesIO(); plt.savefig(buf, format='png', transparent=True); plt.close(fig); buf.seek(0)
         return buf.read()

    labels = list(data.keys())
    values = list(data.values())
    sorted_indices = np.argsort(values)[::-1]
    sorted_labels = [labels[i] for i in sorted_indices]
    sorted_values = [values[i] for i in sorted_indices]
    colors = DARK_MODE_PALETTE * (len(sorted_labels) // len(DARK_MODE_PALETTE) + 1)
    
    fig, ax = plt.subplots(figsize=(7, 7))
    fig.patch.set_alpha(0.0); ax.patch.set_alpha(0.0)

    def make_autopct(val_list):
        def my_autopct(pct): return f'{pct:.0f}%' if pct > 3 else ''
        return my_autopct

    wedges, texts, autotexts = ax.pie(
        sorted_values, labels=sorted_labels, colors=colors[:len(sorted_labels)],
        autopct=make_autopct(sorted_values), startangle=90, counterclock=False,
        pctdistance=0.80, labeldistance=1.25, rotatelabels=True,
        wedgeprops={'width': 0.5, 'edgecolor': '#1e293b', 'linewidth': 2},
        textprops={'color': 'white', 'fontsize': 14, 'fontweight': 'bold'}
    )
    plt.setp(autotexts, size=9, weight="bold", color="white")
    plt.setp(texts, color="#e2e8f0") 
    ax.axis('equal')
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', transparent=True, dpi=100)
    plt.close(fig); buf.seek(0)
    return buf.read()

def bar_chart_top_merchants(categorized_transactions: List[Dict[str, Any]], top_n: int = 5) -> bytes:
    merchant_amounts = defaultdict(float)

    for tx in categorized_transactions:
        # prefer signed_amount if present
        amt = tx.get("signed_amount", None)
        if amt is None:
            try:
                amt = float(tx.get("amount", 0.0))
            except Exception:
                amt = 0.0

        cat = tx.get("category", "Others")
        typ = (tx.get("transaction_type") or "").lower()
        name = tx.get("name", "").strip() or "Unknown"

        # 1. strictly exclude Salary
        if cat == "Salary":
            continue

        # 2. Determine if this tx should be counted as expense:
        # if amt is negative -> expense
        # OR if transaction_type explicitly contains expense keyword -> expense (even if amt positive)
        is_explicit_expense = any(k in typ for k in EXPENSE_KEYWORDS)
        is_explicit_income = any(k in typ for k in INCOME_KEYWORDS)

        if is_explicit_income:
            continue

        if amt < 0:
            merchant_amounts[name] += abs(amt)
        elif is_explicit_expense and amt > 0:
            merchant_amounts[name] += amt

    # Sort and take top N
    top = sorted(merchant_amounts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    names, amounts = ([t[0] for t in top], [t[1] for t in top]) if top else ([], [])

    # Plotting
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    
    if not amounts:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.axis('off')
    else:
        y_pos = np.arange(len(names))
        # Plot bars
        ax.barh(y_pos[::-1], amounts[::-1], color='#3b82f6', height=0.6) 
        
        # Labels and formatting
        ax.set_yticks(y_pos[::-1])
        ax.set_yticklabels(names[::-1], color='white', fontsize=10)
        ax.set_xlabel("Amount Spent (₹)", color='#94a3b8')
        
        # Axis styling
        ax.tick_params(axis='x', colors='#94a3b8')
        ax.tick_params(axis='y', colors='white')
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


def generate_spending_insights(summary: Dict[str, Any]) -> Dict[str, str]:
    """
    Sends the monthly summary to an LLM to generate personalized
    saving advice and cost-cutting tips.
    FIXED: Removed strict JSON mode to prevent 400 Errors.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("ERROR: GROQ_API_KEY is missing.")
        return {
            "cost_cutting": "API Key missing.",
            "saving_strategy": "Unable to generate insights."
        }

    # Prepare Data
    total_income = summary.get("total_received", 0)
    total_spent = summary.get("total_spent", 0)
    savings = summary.get("net_savings", 0)
    
    # Get top 5 categories/merchants
    top_cats = list(summary.get("amount_per_category", {}).items())[:5]
    categories_str = ", ".join([f"{k}: {int(v)}" for k, v in top_cats])
    
    top_merchs = summary.get("top_merchants", [])[:5]
    merchants_str = ", ".join([f"{m['merchant']}" for m in top_merchs])

    # Simplified Prompt
    prompt = (
        f"You are a financial advisor. Analyze this monthly data:\n"
        f"Income: {total_income}, Spent: {total_spent}, Net: {savings}\n"
        f"Top Categories: {categories_str}\n"
        f"Top Merchants: {merchants_str}\n\n"
        "Respond with a valid JSON object containing exactly two keys:\n"
        "1. \"cost_cutting\": (String) Where to cut costs and how.\n"
        "2. \"saving_strategy\": (String) A specific saving rule to follow.\n"
        "Do not include any markdown formatting or backticks. Just the raw JSON."
    )

    url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
    
    # FIX: Removed 'response_format' to stop 400 errors. 
    # Added 'max_tokens' to prevent cutoff.
    payload = {
        "model": "meta-llama/llama-guard-4-12b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 500 
    }
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        raw_content = data["choices"][0]["message"]["content"]
        
        # --- CLEANUP LOGIC ---
        # 1. Remove markdown code blocks if present (```json ... ```)
        clean_content = re.sub(r"```json|```", "", raw_content).strip()
        
        # 2. Parse
        parsed = json.loads(clean_content)
        
        # 3. Validate keys exist
        return {
            "cost_cutting": parsed.get("cost_cutting", "Reduce discretionary spending."),
            "saving_strategy": parsed.get("saving_strategy", "Save 20% of your income.")
        }
        
    except Exception as e:
        print(f"Insight Generation Failed: {e}")
        # Return fallback data so UI doesn't break
        return {
            "cost_cutting": "Consider reducing dining out and subscription costs.",
            "saving_strategy": "Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings."
        }