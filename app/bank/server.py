from fastapi import FastAPI, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.bank.data import MEMBERS


app = FastAPI(title="Demo Core Banking")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Core Banking System</title>
    </head>
    <body>
        <h1>Core Banking System</h1>
        <p>Internal banking operations portal.</p>
        <a href="/members">Member Search</a>
    </body>
    </html>
    """


@app.get("/members", response_class=HTMLResponse)
def members_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Member Search</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background: #f4f4f4;
            }

            .panel {
                background: white;
                border: 1px solid #aaa;
                padding: 25px;
                width: 600px;
            }

            h1 {
                font-size: 24px;
            }

            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }

            input {
                padding: 8px;
                width: 250px;
            }

            button {
                padding: 8px 18px;
                margin-left: 8px;
                cursor: pointer;
            }

            .hint {
                margin-top: 20px;
                color: #666;
                font-size: 13px;
            }
        </style>
    </head>

    <body>
        <div class="panel">
            <h1>Member Search</h1>

            <form action="/members/search" method="get">
                <label for="member-id">Member ID</label>

                <input
                    id="member-id"
                    name="member_id"
                    type="text"
                    autocomplete="off"
                >

                <button type="submit">Search</button>
            </form>

            <div class="hint">
                Enter the member ID to retrieve account information.
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/members/search", response_class=HTMLResponse)
def search_member(member_id: str = Query(...)):
    member_id = member_id.strip()
    member = MEMBERS.get(member_id)

    if member is None:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Member Search</title>
        </head>

        <body>
            <h1>Member Search</h1>

            <div role="alert">
                Member not found.
            </div>

            <p>No member exists for the supplied member ID.</p>

            <a href="/members">Return to Member Search</a>
        </body>
        </html>
        """

    accounts_html = ""

    for account_type, balance in member["accounts"].items():
        accounts_html += f"""
            <tr>
                <th scope="row">{account_type.title()} Balance</th>
                <td class="balance">
                    ${balance:,.2f}
                </td>
            </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Member Details</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background: #f4f4f4;
            }}

            .panel {{
                background: white;
                border: 1px solid #aaa;
                padding: 25px;
                width: 700px;
            }}

            h1 {{
                font-size: 24px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }}

            th, td {{
                border: 1px solid #999;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background: #e8e8e8;
                width: 220px;
            }}

            .balance {{
                font-weight: bold;
            }}

            .actions {{
                margin-top: 25px;
            }}

            .actions a {{
                margin-right: 15px;
            }}
        </style>
    </head>

    <body>
        <div class="panel">
            <h1>Member Details</h1>

            <table>
                <tr>
                    <th scope="row">Member ID</th>
                    <td>{member_id}</td>
                </tr>

                <tr>
                    <th scope="row">Member Name</th>
                    <td>{member["name"]}</td>
                </tr>

                <tr>
                    <th scope="row">Accounts</th>
                    <td>{", ".join(
                        account.title()
                        for account in member["accounts"]
                    )}</td>
                </tr>

                {accounts_html}
            </table>

            <div class="actions">
                <a href="/accounts/add?member_id={member_id}">
                    Add Account
                </a>

                <a href="/members">
                    Search Another Member
                </a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/accounts/add", response_class=HTMLResponse)
def add_account_page(member_id: str = Query(...)):
    if member_id not in MEMBERS:
        return """
        <h1>Member not found.</h1>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Account</title>
    </head>

    <body>
        <h1>Add Account</h1>

        <p>Member ID: {member_id}</p>

        <form action="/accounts/add" method="post">
            <input
                type="hidden"
                name="member_id"
                value="{member_id}"
            >

            <label for="account-type">
                Account Type
            </label>

            <select
                id="account-type"
                name="account_type"
            >
                <option value="checking">Checking</option>
                <option value="savings">Savings</option>
            </select>

            <br><br>

            <label for="initial-deposit">
                Initial Deposit
            </label>

            <input
                id="initial-deposit"
                name="initial_deposit"
                type="number"
                step="0.01"
                value="0"
            >

            <br><br>

            <button type="submit">
                Create Account
            </button>
        </form>

        <br>

        <a href="/members/search?member_id={member_id}">
            Cancel
        </a>
    </body>
    </html>
    """


@app.post("/accounts/add", response_class=HTMLResponse)
def add_account(
    member_id: str = Form(...),
    account_type: str = Form(...),
    initial_deposit: float = Form(...),
):
    member = MEMBERS.get(member_id)

    if member is None:
        return """
        <div role="alert">
            Member not found.
        </div>
        """

    if account_type in member["accounts"]:
        return """
        <div role="alert">
            Account already exists.
        </div>
        """

    if initial_deposit < 0:
        return """
        <div role="alert">
            Initial deposit cannot be negative.
        </div>
        """

    member["accounts"][account_type] = initial_deposit

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Created</title>
    </head>

    <body>
        <h1>Account Created</h1>

        <div role="status">
            {account_type.title()} account created successfully.
        </div>

        <p>
            Member ID: {member_id}
        </p>

        <p>
            Initial Deposit: ${initial_deposit:,.2f}
        </p>

        <a href="/members/search?member_id={member_id}">
            Return to Member Details
        </a>
    </body>
    </html>
    """