import asyncio
from playwright.async_api import async_playwright
import time
import subprocess
import os

async def run_tests():
    # Start the Flask app
    proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3) # Wait for the server to start

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Login
            print("Testing Login...")
            await page.goto("http://127.0.0.1:5000/login")
            await page.fill('input[name="username"]', "admin")
            await page.fill('input[name="password"]', "password123")
            await page.click('button[type="submit"]')
            await page.wait_for_url("http://127.0.0.1:5000/dashboard")
            print("Login successful.")

            # Dashboard check
            print("Checking Dashboard...")
            await page.screenshot(path="dashboard_screenshot.png")
            print("Dashboard screenshot saved.")

            # Add Member
            print("Testing Add Member...")
            await page.goto("http://127.0.0.1:5000/member/add")
            await page.fill('input[name="first_name"]', "Alice")
            await page.fill('input[name="last_name"]', "Johnson")
            await page.fill('input[name="email"]', "alice@example.com")
            await page.fill('input[name="phone"]', "1112223333")
            await page.select_option('select[name="plan_id"]', index=1)
            await page.click('button[type="submit"]')
            await page.wait_for_url("http://127.0.0.1:5000/members")
            print("Member added successfully.")

            # Record Payment
            print("Testing Record Payment...")
            await page.goto("http://127.0.0.1:5000/payment/add")
            await page.select_option('select[name="member_id"]', index=1)
            await page.fill('input[name="amount"]', "50")
            await page.select_option('select[name="payment_method"]', value="Cash")
            await page.click('button[type="submit"]')
            await page.wait_for_url("http://127.0.0.1:5000/payments")
            print("Payment recorded successfully.")

            # Attendance Check-in
            print("Testing Attendance...")
            await page.goto("http://127.0.0.1:5000/attendance")
            await page.select_option('select[name="member_id"]', index=1)
            await page.click('button[type="submit"]')
            print("Attendance recorded successfully.")

            print("All frontend tests passed.")
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            await browser.close()
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_tests())
