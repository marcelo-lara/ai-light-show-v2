from playwright.sync_api import Page, expect

def do_goto(page: Page, base_url: str, goto_value: str):
    """Navigate to the specified path."""
    url = goto_value if goto_value.startswith("http") else f"{base_url}{goto_value}"
    print(f"STEP: goto {url}")
    page.goto(url, wait_until="networkidle")

def do_click(page: Page, click_spec: dict):
    """Click an element based on a role/name or CSS selector."""
    if "role" in click_spec:
        role = click_spec["role"]
        name = click_spec.get("name")
        print(f"STEP: click role={role} name='{name}'")
        page.get_by_role(role, name=name).click()
    elif "css" in click_spec:
        css = click_spec["css"]
        print(f"STEP: click css={css}")
        page.locator(css).click()
    else:
        raise ValueError(f"Invalid click spec: {click_spec}")

def do_expect(page: Page, expect_spec: dict):
    """Assert visibility, count, or text contents."""
    if "visible" in expect_spec:
        css = expect_spec["visible"]["css"]
        print(f"STEP: expect visible css={css}")
        expect(page.locator(css)).to_be_visible()
    elif "text" in expect_spec:
        css = expect_spec["text"]["css"]
        text = expect_spec["text"]["equals"]
        timeout = expect_spec["text"].get("timeout", 5000)
        print(f"STEP: expect text css={css} equals='{text}' timeout={timeout}")
        expect(page.locator(css)).to_have_text(text, timeout=timeout)
    elif "count" in expect_spec:
        css = expect_spec["count"]["css"]
        count = expect_spec["count"]["equals"]
        print(f"STEP: expect count css={css} equals={count}")
        expect(page.locator(css)).to_have_count(count)
    elif "texts" in expect_spec:
        css = expect_spec["texts"]["css"]
        texts = expect_spec["texts"]["equals"]
        print(f"STEP: expect texts css={css} equals={texts}")
        expect(page.locator(css)).to_have_text(texts)
    else:
        raise ValueError(f"Invalid expect spec: {expect_spec}")

def run_step(page: Page, base_url: str, step: dict):
    """Execute a single YAML step."""
    if "goto" in step:
        do_goto(page, base_url, step["goto"])
    elif "click" in step:
        do_click(page, step["click"])
    elif "expect" in step:
        do_expect(page, step["expect"])
    else:
        raise ValueError(f"Unknown directive in step: {step}")
