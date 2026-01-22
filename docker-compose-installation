
```
Docker Compose version v2.40.2
```

This approach follows **Docker’s official plugin-based installation**, which is the **recommended and supported method** for modern Amazon Linux.

---
* **Docker Compose v2** is installed as a **Docker CLI plugin**
* The binary name is:

  ```
  docker compose
  ```

  (space, not hyphen)

---

## Step 1: Update the System

```bash
sudo dnf update -y
```

---

## Step 2: Install Docker Engine

Amazon Linux 2023/2024 provides Docker via `dnf`.

```bash
sudo dnf install docker -y
```

Enable and start Docker:

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

Verify Docker:

```bash
docker --version
```

---

## Step 3: Install Docker Compose v2.40.2 (Official Method)

Create the Docker CLI plugins directory:

```bash
mkdir -p ~/.docker/cli-plugins
```

Download **exactly version v2.40.2**:

```bash
curl -SL https://github.com/docker/compose/releases/download/v2.40.2/docker-compose-linux-x86_64 \
-o ~/.docker/cli-plugins/docker-compose
```

Make it executable:

```bash
chmod +x ~/.docker/cli-plugins/docker-compose
```

---

## Step 4: Verify Docker Compose Version

```bash
docker compose version
```

Expected output:

```
Docker Compose version v2.40.2
```

This now **matches your local system output exactly**.

---

---

## Common Mistake to Avoid

❌ Do NOT expect this to work:

```bash
docker-compose --version
```

✔ Correct command:

```bash
docker compose version
```

