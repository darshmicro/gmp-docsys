"""
SQL Server Connection Diagnostic Tool

WHAT THIS DOES
    Tests your SQL Server connection step by step and tells you, in plain
    language, exactly what's wrong and how to fix it — instead of showing
    you a cryptic technical error message and leaving you to guess.

HOW TO USE IT
    1. Set the same DATABASE_URL you're trying to use in start_server.bat
       (or type it directly when prompted).
    2. Run:
           python test_sql_connection.py
    3. Read the numbered checks. The first one that fails tells you
       exactly what to fix. Fix it, then run this script again — repeat
       until all checks pass.

This script only READS information to test the connection — it does not
create, modify, or delete anything in your database.
"""
import os
import re
import sys


def check_pyodbc_installed():
    print("[1/5] Checking that the 'pyodbc' Python package is installed...")
    try:
        import pyodbc  # noqa
        print("      OK — pyodbc is installed.\n")
        return True
    except ImportError:
        print("      PROBLEM: pyodbc is not installed.")
        print("      FIX: run this command, then try again:")
        print("           pip install pyodbc\n")
        return False


def check_odbc_drivers():
    print("[2/5] Checking which SQL Server ODBC drivers are installed on this computer...")
    import pyodbc
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        print("      PROBLEM: no SQL Server ODBC driver is installed on this computer at all.")
        print("      FIX: search 'Microsoft ODBC Driver 17 for SQL Server download' on the")
        print("           web, download it from Microsoft's own website, and install it.")
        print("           Then run this script again.\n")
        return None
    print("      Found these installed drivers:")
    for d in drivers:
        print(f"        - {d}")
    print()
    return drivers


def get_database_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        print("Using DATABASE_URL from your environment variable.\n")
        return url
    print("DATABASE_URL is not set as an environment variable.")
    url = input("Paste your full connection string here and press Enter:\n> ").strip()
    print()
    return url


def check_url_format(url, available_drivers):
    print("[3/5] Checking the format of your connection string...")
    if not url.startswith("mssql+pyodbc://"):
        print("      PROBLEM: your connection string doesn't start with 'mssql+pyodbc://'.")
        print("      FIX: it should look like this (see Part 6 of the installation guide):")
        print("           mssql+pyodbc://USERNAME:PASSWORD@SERVERNAME/GMPDocTrack?driver=ODBC+Driver+17+for+SQL+Server\n")
        return False

    driver_match = re.search(r"driver=([^&]+)", url)
    if not driver_match:
        print("      PROBLEM: your connection string doesn't specify a driver= value at the end.")
        print("      FIX: add '?driver=ODBC+Driver+17+for+SQL+Server' to the end of it")
        print("           (adjust the number if you installed a different version — see the")
        print("           driver list printed in Check 2 above).\n")
        return False

    requested_driver = driver_match.group(1).replace("+", " ")
    if available_drivers and requested_driver not in available_drivers:
        print(f"      PROBLEM: your connection string asks for '{requested_driver}',")
        print(f"      but that driver is not installed on this computer.")
        print(f"      FIX: change 'driver=' in your connection string to match one of the")
        print(f"           drivers listed in Check 2 above (replace spaces with '+'), for example:")
        if available_drivers:
            print(f"           driver={available_drivers[0].replace(' ', '+')}\n")
        return False

    print("      OK — connection string format looks correct.\n")
    return True


def attempt_connection(url):
    print("[4/5] Attempting to actually connect to SQL Server...")
    print("      (this can take up to 15-30 seconds if something is misconfigured — please wait)")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"timeout": 15})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("      SUCCESS — connected to SQL Server!\n")
        return True, engine
    except Exception as e:
        message = str(e)
        print("      PROBLEM: could not connect. Here's what that error usually means:\n")
        explain_error(message)
        return False, None


def explain_error(message):
    lower = message.lower()

    if "login failed" in lower:
        print("      -> SQL Server IS reachable, but it rejected your username/password.")
        print("      Most likely cause: 'SQL Server Authentication' is not turned on.")
        print("      By default, many SQL Server installs only accept Windows logins, not")
        print("      the kind of username+password login this application uses.")
        print("      FIX:")
        print("        1. Open SQL Server Management Studio (SSMS), right-click the server")
        print("           name at the very top of the left panel, choose Properties.")
        print("        2. Click 'Security' on the left of that dialog.")
        print("        3. Select 'SQL Server and Windows Authentication mode', click OK.")
        print("        4. Restart the SQL Server service: open 'Services' (search it in the")
        print("           Windows Start menu), find 'SQL Server (MSSQLSERVER)' or similar,")
        print("           right-click it, choose Restart.")
        print("        5. Also double-check the exact password in your connection string")
        print("           matches what you set when you ran the CREATE LOGIN line in")
        print("           schema_sqlserver.sql.\n")

    elif "cannot open database" in lower:
        print("      -> SQL Server IS reachable and your login worked, but the specific")
        print("      database named in your connection string doesn't exist (or your login")
        print("      doesn't have permission to use it).")
        print("      FIX: open SSMS, confirm a database literally named 'GMPDocTrack' exists")
        print("      under Databases in the left panel. If not, redo Part 4 of the")
        print("      installation guide.\n")

    elif "named pipes" in lower or "tcp provider" in lower or "could not open a connection" in lower:
        print("      -> Your computer could not reach SQL Server over the network at all.")
        print("      This is almost always one of these three things:")
        print("        A) TCP/IP is turned off in SQL Server's own network settings")
        print("           (very common on a fresh install — off by default).")
        print("           FIX: open 'SQL Server Configuration Manager' (search for it in the")
        print("           Windows Start menu). Expand 'SQL Server Network Configuration',")
        print("           click 'Protocols for MSSQLSERVER' (or your instance name), and make")
        print("           sure 'TCP/IP' says Enabled. If you had to change it, restart the")
        print("           SQL Server service afterward (see Services, as described above).")
        print("        B) The Windows Firewall on the SQL Server computer is blocking the")
        print("           connection. FIX: ask whoever manages that firewall to allow incoming")
        print("           connections on TCP port 1433 (the standard SQL Server port).")
        print("        C) The server name in your connection string is wrong. If SQL Server")
        print("           was installed as a 'named instance' (common with SQL Server")
        print("           Express), you must include the instance name, e.g.")
        print("           'MYSERVER\\\\SQLEXPRESS', not just 'MYSERVER'. You can also confirm")
        print("           the exact server name by opening SSMS and looking at what you")
        print("           typed into the 'Server name' box when it connected successfully.\n")

    elif "ssl provider" in lower or "certificate" in lower:
        print("      -> This is a newer, very common issue: recent ODBC drivers require an")
        print("      encrypted connection by default, and reject connecting to a server")
        print("      whose certificate isn't from a recognized authority — which is normal")
        print("      for an internal company server with no public certificate.")
        print("      FIX: add this to the END of your connection string:")
        print("           &TrustServerCertificate=yes")
        print("      Example:")
        print("           mssql+pyodbc://user:pass@SERVER/GMPDocTrack?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes\n")

    elif "timeout" in lower:
        print("      -> The connection attempt took too long and gave up. This usually means")
        print("      either the server name/address is wrong, or a firewall is silently")
        print("      dropping the connection rather than rejecting it outright.")
        print("      FIX: double check the server name, and see point (B) above about the")
        print("      Windows Firewall allowing TCP port 1433.\n")

    else:
        print("      This error didn't match any of the common patterns this tool")
        print("      recognizes. Here's the exact technical message — copy this and share")
        print("      it (with me, or your IT support) for a precise diagnosis:\n")
        print(f"      {message}\n")


def check_can_see_tables(engine):
    print("[5/5] Checking that the expected tables exist in this database...")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = {"documents", "document_copies", "audit_trail", "users", "storage_rooms"}
    missing = expected - set(tables)
    if missing:
        print(f"      PROBLEM: connected successfully, but these expected tables are")
        print(f"      missing: {', '.join(sorted(missing))}")
        print("      FIX: you connected to the right server, but schema_sqlserver.sql hasn't")
        print("      been run against this database yet — see Part 4 of the installation guide.\n")
        return False
    print(f"      OK — found all expected tables ({len(tables)} tables total).\n")
    return True


def main():
    print("=" * 70)
    print("SQL Server Connection Diagnostic Tool")
    print("=" * 70)
    print()

    if not check_pyodbc_installed():
        sys.exit(1)

    drivers = check_odbc_drivers()

    url = get_database_url()

    if not check_url_format(url, drivers):
        sys.exit(1)

    success, engine = attempt_connection(url)
    if not success:
        sys.exit(1)

    check_can_see_tables(engine)

    print("=" * 70)
    print("All checks passed. Your DATABASE_URL is correctly configured.")
    print("Use this exact same value in start_server.bat.")
    print("=" * 70)


if __name__ == "__main__":
    main()
