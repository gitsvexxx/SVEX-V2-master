with open('SVEX_APP/templates/SVEX_APP/manager_home.html', 'r') as f:
    content = f.read()

old_th = '<th style="padding: 12px; border-bottom: 2px solid #e2e8f0;">User</th>'
new_th = '<th style="padding: 12px; border-bottom: 2px solid #e2e8f0; text-align: center;">Status</th>\n                            <th style="padding: 12px; border-bottom: 2px solid #e2e8f0;">User</th>'

old_td = '<td style="padding: 12px;"><strong>{{ u.username }}</strong><br><small style="color:#64748b;">{{ u.email }}</small></td>'
new_td = """<td style="padding: 12px; text-align: center;">
                                {% if u.is_active %}
                                <div style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; margin: 0 auto; box-shadow: 0 0 6px #10b981;"></div>
                                <small style="color: #10b981; display: block; margin-top: 4px; font-size: 11px;">Online</small>
                                {% else %}
                                <div style="width: 10px; height: 10px; border-radius: 50%; background: #94a3b8; margin: 0 auto;"></div>
                                <small style="color: #64748b; display: block; margin-top: 4px; font-size: 11px;">{{ u.last_active_str }}</small>
                                {% endif %}
                            </td>
                            <td style="padding: 12px;"><strong>{{ u.username }}</strong><br><small style="color:#64748b;">{{ u.email }}</small></td>"""

content = content.replace(old_th, new_th).replace(old_td, new_td)
content = content.replace('<td colspan="6"', '<td colspan="7"')

with open('SVEX_APP/templates/SVEX_APP/manager_home.html', 'w') as f:
    f.write(content)
