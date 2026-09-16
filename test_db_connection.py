"""
SQL Server Connection Diagnostic Tool

WHAT THIS DOES
    Tests your SQL Server connection step by step, in isolation from the
    main application, so you get a clear answer about exactly what's
    wrong instead of a long Python error message.

HOW TO USE IT (recommended way — handles special characters in your
password automatically, no manual encoding ever needed)
    1. Open Command Prompt, `cd` into the gmp-docsystem folder.
    2. Set these four values (type your password exactly as-is, even if
       it contains @ : / # % or anything else):
       set DB_SERVER=YOUR_SERVER_NAME
       set DB_NAME=GMPDocTrack
       set DB_USER=svc_gmpdoctrack
       set DB_PASSWORD=YourActualPassword
    3. Run:
       python test_db_connection.py
    4. Read the output — it walks through each check and tells you
       exactly which step failed and what to do about it.

ALTERNATIVE: if you're using a single DATABASE_URL string instead (the
older approach), this tool still supports that too — but if your password
contains @ : / # or %, you must have already percent-encoded it yourself
in that string, or this tool will detect and flag the problem below.

You can run this over and over as you fix each issue, without needing to
start the whole application each time.
"""
import os
import re
import socket
import sys

# Reuse the exact same URL-building logic the real application uses, so
# this diagnostic tool is always testing precisely what the app will
# actually do — never a hand-rolled approximation that could drift out of
# sync or (worse) parse things differently than the real app does.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def fail(title, explanation, fix_steps):
    print()
    print(f"❌ {title}")
    if explanation:
        print(f"   {explanation}")
    print()
    print("   What to do:")
    for i, step in enumerate(fix_steps, 1):
        print(f"   {i}. {step}")
    print()
    sys.exit(1)


def ok(message):
    print(f"✅ {message}")


def resolve_named_instance_port(server_ip, instance_name, timeout=4):
    """
    Implements the SQL Server Browser protocol (SSRP) over UDP port 1434 —
    this is exactly what the real ODBC driver does internally before
    connecting to a named instance, and it's the only correct way to find
    out which TCP port that instance is actually using. A named instance's
    port changes every time SQL Server restarts, so checking a fixed port
    number (like 1433) is meaningless for named instances.

    Returns (port, detail) — port is None if the lookup failed, and
    `detail` is either the raw response payload (on success) or an error
    description (on failure), useful for troubleshooting either way.
    """
    import struct

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        # 0x04 = CLNT_UCAST_INST: "tell me about this ONE specific instance"
        message = bytes([0x04]) + instance_name.encode("ascii")
        sock.sendto(message, (server_ip, 1434))
        data, _ = sock.recvfrom(4096)
    except socket.timeout:
        return None, "no response within timeout (request may be blocked by a firewall)"
    except Exception as e:
        return None, str(e)
    finally:
        sock.close()

    if len(data) < 3 or data[0] != 0x05:
        return None, "received a response, but not in the expected format"

    length = struct.unpack("<H", data[1:3])[0]
    payload = data[3:3 + length].decode("ascii", errors="replace")
    parts = payload.split(";")
    for i, part in enumerate(parts):
        if part.lower() == "tcp" and i + 1 < len(parts) and parts[i + 1].isdigit():
            return int(parts[i + 1]), payload
    return None, f"response didn't include a tcp port: {payload}"


def check_for_unencoded_at_symbol():
    """The single most common cause of a badly-broken connection string:
    an @ symbol typed directly into DATABASE_URL's password, without
    percent-encoding it as %40 first. This doesn't raise an error when
    parsed — it just silently produces the wrong host/password — so it
    needs an explicit, deliberate check rather than relying on some other
    error message to hint at it."""
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url or "://" not in raw_url:
        return
    remainder = raw_url.split("://", 1)[1]
    # A well-formed url has exactly one @ separating credentials from the
    # host. More than one means something before the real @ contains an
    # unencoded @ of its own — almost always the password.
    if remainder.count("@") > 1:
        fail(
            "Your DATABASE_URL password contains an unencoded @ symbol",
            "An @ symbol has special meaning in a connection string (it marks "
            "where the password ends and the server name begins), so an @ "
            "inside your actual password confuses the parser — it silently "
            "produces the wrong server name instead of giving a clear error, "
            "which is why this can look like a 'server not found' problem.",
            [
                "EASIEST FIX: switch to the separate DB_SERVER / DB_NAME / "
                "DB_USER / DB_PASSWORD settings instead of one DATABASE_URL "
                "string — see the top of this file, or start_server.bat, for "
                "the exact format. With that approach you type your password "
                "exactly as-is and never need to encode anything.",
                "OR, if you want to keep using a single DATABASE_URL string, "
                "replace every @ in your password specifically with %40 "
                "(and : with %3A, / with %2F, # with %23, % with %25, if your "
                "password contains those too), then try again.",
            ],
        )


def main():
    print("=" * 70)
    print("SQL Server Connection Diagnostic")
    print("=" * 70)

    check_for_unencoded_at_symbol()

    try:
        from app.db_url import build_database_url
    except Exception as e:
        fail(
            "Could not load the application's database configuration",
            str(e),
            ["Make sure you're running this from inside the gmp-docsystem folder."],
        )

    database_url = build_database_url()

    if database_url.startswith("sqlite"):
        fail(
            "No SQL Server settings found — currently configured for the local file",
            "Neither DATABASE_URL nor DB_SERVER is set in this Command Prompt "
            "window, so the application would fall back to the local SQLite "
            "file, not SQL Server.",
            [
                "Set the four DB_ values first (see the top of this file for "
                "the exact format), then run this script again.",
            ],
        )

    from sqlalchemy.engine.url import make_url
    url = make_url(database_url)
    print(f"Testing connection to: {url.render_as_string(hide_password=True)}")
    print()

    if "YOUR_SERVER_NAME" in database_url or "CHANGE_THIS_PASSWORD" in database_url:
        fail(
            "Your connection settings still have placeholder text in them",
            "It looks like YOUR_SERVER_NAME or CHANGE_THIS_PASSWORD wasn't "
            "replaced with your real values.",
            [
                "Open start_server.bat and replace both placeholders with "
                "your actual server name and the password you set when "
                "creating the svc_gmpdoctrack login.",
            ],
        )

    host = url.host
    explicit_port = url.port  # only set if the connection string had host:port explicitly
    instance = None
    if host and "\\" in host:
        host, instance = host.split("\\", 1)

    print(f"Server name found:    {host}")
    print(f"Named instance found: {instance or '(none — using default instance)'}")
    print()

    # ---- STEP 1: can we even reach that computer on the network at all? ----
    print("Step 1: Checking basic network connectivity...")
    try:
        resolved_ip = socket.gethostbyname(host)
        ok(f"Server name '{host}' resolves to IP address {resolved_ip}")
    except socket.gaierror:
        fail(
            f"Could not find a computer named '{host}' on the network",
            "This is the single most common cause of 'Error Locating "
            "Server/Instance Specified'.",
            [
                f"Double check the server name — on the SQL Server machine, open Command "
                f"Prompt and type: hostname   — use that EXACT text.",
                "If you're not sure, open SSMS, look at the 'Connect to Server' box you "
                "use successfully today, and copy that exact Server name value.",
                "If SQL Server is on this SAME computer you're testing from, try using "
                "just a period (.) or 'localhost' instead of a computer name.",
            ],
        )

    # ---- STEP 2: find (or confirm) the actual TCP port, then check it ----
    # A named instance does NOT listen on 1433 — it listens on a different
    # port assigned randomly every time SQL Server starts. The only correct
    # way to find that port is to ask the SQL Server Browser service over
    # UDP port 1434, exactly the way the real ODBC driver does internally
    # before it ever opens the real connection. Testing a fixed port (like
    # 1433) for a named instance tells you nothing useful either way.
    if explicit_port:
        port = explicit_port
        print(f"Step 2: Checking if port {port} (explicitly set in your connection string) is open on {host}...")
        target_port = port
    elif instance:
        print(f"Step 2: Asking SQL Server Browser (UDP port 1434) which TCP port instance "
              f"'{instance}' is actually using...")
        target_port, browser_detail = resolve_named_instance_port(resolved_ip, instance)
        if target_port is None:
            if browser_detail.startswith("no response within timeout"):
                # Genuinely no reply came back at all — this really is most
                # likely a firewall silently dropping the UDP request.
                fail(
                    f"SQL Server Browser did not answer at all for instance '{instance}'",
                    "The UDP request this test sent to port 1434 on the server got no reply "
                    "whatsoever — no error, just silence. That specific symptom is almost "
                    "always something dropping the request in transit, not SQL Server itself.",
                    [
                        "This is almost always Windows Firewall on the SQL SERVER machine "
                        "blocking the request — note this is a DIFFERENT setting from the "
                        "TCP/IP protocol setting inside SQL Server Configuration Manager, "
                        "which only controls whether SQL Server listens at all, not whether "
                        "the Windows firewall lets other computers reach it.",
                        "On the SQL Server machine, open 'Windows Defender Firewall with "
                        "Advanced Security' (search for it in the Start menu).",
                        "Click 'Inbound Rules' on the left, then 'New Rule...' on the right.",
                        "Choose 'Port' → Next → 'UDP' → Specific local ports: 1434 → Next → "
                        "'Allow the connection' → Next → tick all three profiles → Next → "
                        "name it 'SQL Server Browser' → Finish.",
                        "Create a SECOND rule the same way, but choose 'Program' instead of "
                        "'Port', and browse to sqlservr.exe (usually under "
                        "C:\\Program Files\\Microsoft SQL Server\\MSSQLxx.SQLEXPRESS\\MSSQL\\Binn\\) "
                        "— this covers the actual data connection, whatever port it ends up using.",
                        "If this server and the computer running the app are on different "
                        "network segments/VLANs, also confirm with whoever manages your "
                        "network that traffic between them isn't blocked at the router level.",
                        "Try this test again after adding both firewall rules.",
                    ],
                )
            elif browser_detail.startswith("response didn't include a tcp port"):
                # Browser DID answer — it clearly knows this instance exists
                # (the response even lists its version). It just has no TCP
                # endpoint to report, which means the instance itself isn't
                # actually listening for TCP/IP connections right now.
                fail(
                    f"SQL Server Browser answered, but instance '{instance}' isn't listening on any TCP port",
                    "This is good news in one sense — nothing is blocking your request; the "
                    "server replied normally and even confirmed the instance exists "
                    f"(detail: {browser_detail}). It just has no network port to report, "
                    "which means TCP/IP connections aren't actually active for this instance "
                    "right now — this is NOT a firewall issue, so firewall rules won't fix it.",
                    [
                        "Open 'SQL Server Configuration Manager' on the SQL Server machine.",
                        "Click 'SQL Server Network Configuration' → 'Protocols for "
                        f"{instance}' on the left.",
                        "Look at TCP/IP on the right — if it says Disabled, right-click it → "
                        "Enable.",
                        "This change does NOT take effect until you restart the service: click "
                        "'SQL Server Services' on the left, find your instance (e.g. 'SQL "
                        f"Server ({instance})'), right-click → Restart.",
                        "If TCP/IP already showed Enabled: the service may simply not be "
                        "running at all right now — in that same 'SQL Server Services' list, "
                        "confirm it says 'Running,' not 'Stopped,' and start it if needed.",
                        "Try this test again after restarting the service.",
                    ],
                )
            else:
                fail(
                    f"SQL Server Browser lookup failed for instance '{instance}'",
                    f"Detail: {browser_detail}",
                    [
                        "This didn't match a known pattern — copy the exact detail message "
                        "above when asking for further help.",
                    ],
                )
        ok(f"SQL Server Browser reports instance '{instance}' is listening on TCP port {target_port}")
        port = target_port
    else:
        port = 1433
        print(f"Step 2: Checking if port {port} is open on {host}...")
        target_port = port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((resolved_ip, target_port))
    sock.close()

    if result != 0:
        if instance and not explicit_port:
            fail(
                f"SQL Server Browser said port {target_port} is correct, but nothing answers there",
                "Browser found the right port, but a connection to that exact port "
                "was refused or timed out — this points specifically at the actual "
                "SQL Server data port being blocked, even though the Browser lookup "
                "itself got through.",
                [
                    "Add the 'Program' firewall rule for sqlservr.exe described above, "
                    "if you haven't already — this is very likely the same firewall "
                    "blocking this specific port too.",
                    "Confirm the SQL Server service itself is running: Windows key → "
                    "services.msc → find 'SQL Server (SQLEXPRESS)' → should say Running.",
                ],
            )
        else:
            fail(
                f"Nothing is responding on port {port} at {host}",
                "The computer is reachable, but SQL Server doesn't seem to be listening "
                "on the port we tried.",
                [
                    "Make sure the SQL Server service is actually running: Windows key → "
                    "services.msc → find 'SQL Server (MSSQLSERVER)' → confirm it says "
                    "Running (right-click → Start if not).",
                    "Open 'SQL Server Configuration Manager' → SQL Server Network "
                    "Configuration → Protocols → make sure TCP/IP is Enabled, then restart "
                    "the SQL Server service.",
                    "If SQL Server is on a different computer than this one, ask whoever "
                    "manages that computer's firewall to allow incoming connections on "
                    f"TCP port {port}.",
                ],
            )
    ok(f"Something is listening on {host}:{target_port} — network path is open.")

    # ---- STEP 3: can we actually log in and query? ----
    print("\nStep 3: Attempting an actual SQL Server login...")
    try:
        import pyodbc  # noqa: F401
    except ImportError:
        fail(
            "The 'pyodbc' package isn't installed",
            "This is the piece that lets Python talk to SQL Server specifically — "
            "it's a separate install from the main application requirements.",
            [
                "Run: pip install pyodbc",
                "If that fails with a build error, you likely also need the "
                "'Microsoft ODBC Driver 17 for SQL Server' installed — search for "
                "that exact name on Microsoft's website and install it, then try "
                "pip install pyodbc again.",
            ],
        )

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url, connect_args={"timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ok("Successfully logged in and ran a test query!")
    except Exception as e:
        msg = str(e)
        if "Login failed" in msg:
            fail(
                "The server was reached, but the login was rejected",
                "This means networking is fine — the username or password is wrong, "
                "or SQL Server isn't set up to accept this kind of login at all.",
                [
                    "Double-check the password matches exactly what you set when you ran "
                    "'CREATE LOGIN [svc_gmpdoctrack] ...' in Part 4.",
                    "In SSMS, right-click the server name (top of Object Explorer) → "
                    "Properties → Security → confirm 'SQL Server and Windows "
                    "Authentication mode' is selected (not Windows-only). If you change "
                    "this, restart the SQL Server service afterward.",
                ],
            )
        elif "Cannot open database" in msg:
            fail(
                "Logged in successfully, but the GMPDocTrack database wasn't found",
                "Your login credentials work — the database itself doesn't exist yet, "
                "or its name doesn't match.",
                [
                    "Open SSMS, check the Databases list for the exact name — it should "
                    "be GMPDocTrack.",
                    "If it's missing, redo Part 4 of the installation guide (create the "
                    "database and run schema_sqlserver.sql against it).",
                ],
            )
        else:
            fail(
                "Connection failed for an unexpected reason",
                "Networking and the basic setup look fine, so this needs a closer look.",
                [
                    "Copy the exact error text below and share it for a specific diagnosis:",
                    f"  {msg[:300]}",
                ],
            )

    print()
    print("=" * 70)
    print("ALL CHECKS PASSED — your database settings are correctly configured.")
    print("You can now run start_server.bat and it will use SQL Server.")
    print("=" * 70)


if __name__ == "__main__":
    main()
