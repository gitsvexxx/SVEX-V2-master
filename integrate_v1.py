import re
from pathlib import Path

dashboard_path = (
    Path(__file__).resolve().parent
    / "SVEX_APP"
    / "templates"
    / "SVEX_APP"
    / "dashboard"
    / "dashboard.html"
)

with dashboard_path.open("r") as f:
    content = f.read()

# 1. Inject CSS
css_to_inject = """
    /* V1 Slide Modal Styling */
    .slide-modal {
        position: fixed; bottom: -100%; left: 0; width: 100%; height: 85%;
        background: #ffffff; border-top-left-radius: 32px; border-top-right-radius: 32px;
        box-shadow: 0 -10px 40px rgba(0,0,0,0.2);
        transition: bottom 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        z-index: 1000; padding: 32px 24px; box-sizing: border-box;
    }
    .slide-modal.active { bottom: 0; }
    
    .big-primary-btn {
        display: block; width: 100%; background-color: #3b82f6; color: white;
        padding: 18px; border-radius: 16px; font-size: 18px; font-weight: 700;
        text-decoration: none; box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.39);
        margin-bottom: 16px; border: none; cursor: pointer;
    }
    .big-secondary-btn {
        display: block; width: 100%; background-color: #f1f5f9; color: #64748b;
        padding: 16px; border-radius: 16px; font-size: 16px; font-weight: 600;
        text-decoration: none; border: none; cursor: pointer; text-align: center;
    }
    .otp-container { display: flex; justify-content: space-between; margin: 24px 0; }
    .otp-box { width: 45px; height: 55px; border: 2px solid #e2e8f0; border-radius: 12px; font-size: 24px; font-weight: 700; text-align: center; background: #f8fafc; }
"""
if ".slide-modal" not in content:
    content = content.replace("</style>", css_to_inject + "\n</style>")

# 2. Inject HTML Modal
html_modal = """
    <!-- V1 Frictionless Modal (Slide up) -->
    <div id="withdraw-modal" class="slide-modal">
        <div style="width: 40px; height: 5px; background: #e2e8f0; border-radius: 10px; margin: 0 auto 24px auto;"></div>
        
        <!-- Withdraw Form Content -->
        <div id="modal-form-content">
            <h2 style="margin: 0 0 8px 0; font-size: 24px; color: #0f172a; text-align: center;">Withdraw Funds</h2>
            <p style="margin: 0 0 24px 0; color: #64748b; text-align: center; font-size: 15px;">Amount is pre-filled to your maximum balance.</p>
            
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 32px; font-weight: 800; color: #0f172a;">${{ total_usd_value|floatformat:2|default:"0.00" }}</span>
            </div>
            
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 8px;">IBAN / Account Number</label>
                <input type="text" placeholder="DE89 1234 5678..." style="width: 100%; padding: 16px; border-radius: 12px; border: 1px solid #cbd5e1; font-size: 16px; box-sizing: border-box;">
            </div>
            
            <div style="margin-bottom: 32px;">
                <label style="display: block; font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 8px;">Account Holder Name</label>
                <input type="text" value="{{ user.username|default:user.email }}" style="width: 100%; padding: 16px; border-radius: 12px; border: 1px solid #cbd5e1; font-size: 16px; box-sizing: border-box;">
            </div>
            
            <button class="big-primary-btn" onclick="showSecurity()">Confirm Details</button>
            <button class="big-secondary-btn" style="background: transparent;" onclick="hideModal()">Cancel</button>
        </div>

        <!-- Security Check -->
        <div id="modal-security-content" style="display: none;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="width: 64px; height: 64px; background: #eff6ff; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto;">
                    <svg width="32" height="32" fill="none" stroke="#3b82f6" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                </div>
                <h2 style="margin: 0 0 8px 0; font-size: 24px; color: #0f172a;">Security Verification</h2>
                <p style="margin: 0; color: #64748b; font-size: 15px;">To complete this withdrawal securely, please enter the 6-digit code sent to your email.</p>
            </div>
            
            <div class="otp-container">
                <input type="text" maxlength="1" class="otp-box" value="">
                <input type="text" maxlength="1" class="otp-box" value="">
                <input type="text" maxlength="1" class="otp-box" value="">
                <input type="text" maxlength="1" class="otp-box" value="">
                <input type="text" maxlength="1" class="otp-box" value="">
                <input type="text" maxlength="1" class="otp-box" value="">
            </div>
            
            <button class="big-primary-btn" onclick="submitFinalWithdrawal()">Submit Withdrawal</button>
            <button class="big-secondary-btn" style="background: transparent;" onclick="hideModal()">Cancel</button>
        </div>
    </div>
"""

js_modal = """
<script>
    function showModal() {
        document.getElementById('withdraw-modal').classList.add('active');
        document.getElementById('modal-form-content').style.display = 'block';
        document.getElementById('modal-security-content').style.display = 'none';
        
        // Setup OTP auto-focus logic
        const otpInputs = document.querySelectorAll('.otp-box');
        otpInputs.forEach((input, index) => {
            input.addEventListener('keyup', (e) => {
                if (e.key >= 0 && e.key <= 9 && index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                } else if (e.key === 'Backspace' && index > 0) {
                    otpInputs[index - 1].focus();
                }
            });
        });
    }
    
    function hideModal() {
        document.getElementById('withdraw-modal').classList.remove('active');
    }
    
    function showSecurity() {
        document.getElementById('modal-form-content').style.display = 'none';
        document.getElementById('modal-security-content').style.display = 'block';
        setTimeout(() => document.querySelectorAll('.otp-box')[0].focus(), 100);
    }
    
    function submitFinalWithdrawal() {
        alert('Withdrawal Submitted Successfully!');
        hideModal();
    }
</script>
"""

# Find the end of revolut-mobile-only div
if 'id="withdraw-modal"' not in content:
    # insert before the closing block content
    content = content.replace("{% endblock %}", html_modal + js_modal + "\n{% endblock %}")

# 3. Change Links
# In the quick action row
content = content.replace('<a href="/dashboard/wallets/withdraw" class="revolut-action-btn">', '<a href="#" onclick="event.preventDefault(); showModal();" class="revolut-action-btn">')

# Also modify any other withdraw buttons on the dashboard (e.g. recent activity or bottom area)
content = content.replace('<a href="/dashboard/wallets/withdraw" class="btn-secondary">Withdraw</a>', '<a href="#" onclick="event.preventDefault(); showModal();" class="btn-secondary">Withdraw</a>')

with dashboard_path.open("w") as f:
    f.write(content)

print("Injected V1 successfully!")
