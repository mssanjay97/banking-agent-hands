from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

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
                    <th scope="row">Account Type</th>
                    <td>{member["account_type"]}</td>
                </tr>

                <tr>
                    <th scope="row">Checking Balance</th>
                    <td class="balance">
                        ${member["checking_balance"]:,.2f}
                    </td>
                </tr>

                <tr>
                    <th scope="row">Savings Balance</th>
                    <td class="balance" data-field="savings-balance">
                        ${member["savings_balance"]:,.2f}
                    </td>
                </tr>
            </table>

            <br>

            <a href="/members">Search Another Member</a>
        </div>
    </body>
    </html>
    """