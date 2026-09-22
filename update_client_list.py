with open('SVEX_APP/templates/SVEX_APP/client_list.html', 'r') as f:
    content = f.read()

# Add Username and Email headers
old_headers = """                    <tr>
                        <th>Client Number</th>
                        <th>First Name</th>
                        <th>Last Name</th>"""
new_headers = """                    <tr>
                        <th>Client Number</th>
                        <th>Username / Email</th>
                        <th>First Name</th>
                        <th>Last Name</th>"""

content = content.replace(old_headers, new_headers)

# Add Username and Email data
old_data = """                    <tr>
                        <td>{{ client.client_number }}</td>
                        <td>{{ client.first_name }}</td>
                        <td>{{ client.last_name }}</td>"""
new_data = """                    <tr>
                        <td style="font-family: monospace;">{{ client.client_number }}</td>
                        <td>
                            <strong>{{ client.user.username }}</strong><br>
                            <small style="color: #64748b;">{{ client.user.email }}</small>
                        </td>
                        <td>{{ client.first_name|default:"-" }}</td>
                        <td>{{ client.last_name|default:"-" }}</td>"""

content = content.replace(old_data, new_data)
content = content.replace('<td colspan="9"', '<td colspan="10"')

with open('SVEX_APP/templates/SVEX_APP/client_list.html', 'w') as f:
    f.write(content)
