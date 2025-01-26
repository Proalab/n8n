# Ansible Server Setup for Docker-Based Deployments

This repository contains an Ansible playbook for setting up a Debian 12 server with Docker, Docker Compose, Cockpit, and n8n.

## Prerequisites

### Local Machine Requirements
1. **Operating System**: Linux or macOS.
2. **Installed Tools**:
   - [Python 3](https://www.python.org/)
   - [pip](https://pip.pypa.io/en/stable/)
   - [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/)

### Remote Server Requirements
1. A Debian 12 server (e.g., Hetzner CPX31).
2. SSH access with a private-public key pair.

## Installation

### 1. Install Ansible on Your Local Machine
```bash
# Update package list
sudo apt update

# Install Ansible
sudo apt install -y ansible
```

For macOS:
```bash
brew install ansible
```

### 2. Clone This Repository
```bash
git clone <repository_url>
cd <repository_directory>
```

### 3. Configure Inventory File
Edit the `inventory` file to include your server's details:
```ini
[servers]
your_server_ip ansible_user=root
```
Replace `your_server_ip` with your server's IP address.

### 4. Test Connection
Verify Ansible can connect to the server:
```bash
ansible all -i inventory -m ping
```

## Usage

### 1. Run the Playbook
Execute the Ansible playbook to configure the server:
```bash
ansible-playbook -i inventory n8n-server.yml
```

### 2. Monitor Progress
The playbook will:
- Configure the hostname.
- Set up a deploy user.
- Install Docker and Docker Compose.
- Install and configure Cockpit.
- Deploy n8n using Docker Compose.

### 3. Verify Installation
- SSH into the server and check:
  ```bash
  docker ps
  ```
- Open the Cockpit interface at `https://your_server_ip:9090`.
- Access the n8n service at your domain or IP address.

## Notes
- Modify `n8n-server.yml` as needed for your specific requirements.
- Ensure the `n8n_directory` variable in the playbook points to the correct location if you change it.

## Troubleshooting

### Common Issues
- **Permission Denied**: Ensure the SSH key has proper permissions and is added to the server.
- **Docker Pull Issues**: Verify the server has internet access.

### Commands to Debug
- Check Docker container status:
  ```bash
  docker ps -a
  ```
- View Ansible logs:
  ```bash
  ansible-playbook -i inventory n8n-server.yml -vvv
  ```

## License
This project is licensed under the MIT License. See `LICENSE` for details.

---

Contributions are welcome! Feel free to open issues or submit pull requests.
