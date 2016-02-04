

def patch():
    import session_csrf
    session_csrf.monkeypatch()
