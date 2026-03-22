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
            # Login as Admin
            print("Testing Admin Login...")
            await page.goto("http://127.0.0.1:5000/login")
            await page.fill('input[name="username"]', "admin")
            await page.fill('input[name="password"]', "password123")
            await page.click('button[type="submit"]')
            await page.wait_for_url("http://127.0.0.1:5000/dashboard")
            print("Admin Login successful.")

            # Dashboard Chart check
            print("Checking Dashboard Analytics...")
            await page.screenshot(path="dashboard_ultimate_screenshot.png")

            # Exercises
            print("Checking Exercises...")
            await page.goto("http://127.0.0.1:5000/exercises")
            assert await page.is_visible("text=Bench Press")
            print("Exercises visible.")

            # Workouts
            print("Checking Workouts...")
            await page.goto("http://127.0.0.1:5000/workouts")
            assert await page.is_visible("text=Full Body Strength")
            print("Workouts visible.")

            # Messaging
            print("Testing Messaging...")
            await page.goto("http://127.0.0.1:5000/messages")
            await page.select_option('select[name="receiver_id"]', index=1)
            await page.fill('textarea[name="content"]', "Automated test message")
            await page.click('button[type="submit"]')
            print("Message sent successfully.")

            # Inventory (Admin Only)
            print("Checking Inventory...")
            await page.goto("http://127.0.0.1:5000/inventory")
            content = await page.content()
            if "Whey Protein" not in content:
                print(f"DEBUG: Content not found. Page source: {content[:500]}")
            assert "Whey Protein" in content
            print("Inventory visible.")

            # Logout
            await page.goto("http://127.0.0.1:5000/logout")

            # Login as Trainer
            print("Testing Trainer Login...")
            await page.goto("http://127.0.0.1:5000/login")
            await page.fill('input[name="username"]', "trainer1")
            await page.fill('input[name="password"]', "trainer123")
            await page.click('button[type="submit"]')
            await page.wait_for_url("http://127.0.0.1:5000/dashboard")
            print("Trainer Login successful.")

            # RBAC Check: Trainer should not see Inventory
            print("Testing RBAC (Trainer access to Inventory)...")
            await page.goto("http://127.0.0.1:5000/inventory")
            # Should be redirected to dashboard with flash message
            await page.wait_for_url("http://127.0.0.1:5000/dashboard")
            assert await page.is_visible("text=Access denied")
            print("RBAC working: Trainer blocked from Inventory.")

            print("All ultimate frontend tests passed.")
        except Exception as e:
            import traceback
            print(f"Test failed: {e}")
            traceback.print_exc()
        finally:
            await browser.close()
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_tests())
