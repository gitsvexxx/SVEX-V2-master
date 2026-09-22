with open('SVEX_APP/templates/SVEX_APP/client_credentials.html', 'r') as f:
    content = f.read()

content = content.replace('<th>Username</th>', '<th>Status</th>\n                        <th>Username</th>')
content = content.replace('{{ credential.username }}</strong><br>', '{{ credential.username }}</strong><br>')

old_td = """<td style="padding: 1rem; color: #d4d4d4; font-weight: 500;">
                            <strong>{{ credential.username }}</strong><br>
                            <small style="color: #737373;">{{ credential.email }}</small>
                        </td>"""

new_td = """<td style="padding: 1rem; text-align: center;">
                            {% if credential.is_active %}
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; margin: 0 auto; box-shadow: 0 0 8px #10b981;"></div>
                            <small style="color: #10b981; display: block; margin-top: 4px;">Online</small>
                            {% else %}
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: #52525b; margin: 0 auto;"></div>
                            <small style="color: #737373; display: block; margin-top: 4px;">{{ credential.last_active_str }}</small>
                            {% endif %}
                        </td>
                        <td style="padding: 1rem; color: #d4d4d4; font-weight: 500;">
                            <strong>{{ credential.username }}</strong><br>
                            <small style="color: #737373;">{{ credential.email }}</small>
                        </td>"""
content = content.replace(old_td, new_td)
content = content.replace('<th style="padding: 1rem; text-align: left; color: #e5e5e5; font-weight: 600; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em;">Username</th>', '<th style="padding: 1rem; text-align: center; color: #e5e5e5; font-weight: 600; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; width: 80px;">Status</th>\n                        <th style="padding: 1rem; text-align: left; color: #e5e5e5; font-weight: 600; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em;">User</th>')

with open('SVEX_APP/templates/SVEX_APP/client_credentials.html', 'w') as f:
    f.write(content)
