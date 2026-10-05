# Deploying ResultCloud on AWS

Region used throughout: **Asia Pacific (Mumbai) `ap-south-1`**. Pick it in the top-right of the AWS console
before every step. All sizes below are free-tier eligible.

```
Internet ──► EC2 (Nginx :80 ─► Gunicorn ─► Flask + React build)
               │  IAM role (no keys on the server)
               ├──► RDS MySQL      (private, only reachable from EC2)
               ├──► S3 bucket      (marksheet PDFs, private + encrypted)
               └──► CloudWatch     (CPU/health metrics, app + Nginx logs)
```

> Tip: sign in to the console as an IAM user with admin rights rather than the root account
> (IAM → Users → Create user → attach `AdministratorAccess`, enable console access).

---

## 1. S3 — bucket for marksheets

1. **S3 → Create bucket**
2. Name: `resultcloud-marksheets-<your-sap-id>` (bucket names are global, so it must be unique)
3. Region: `ap-south-1`
4. **Block all public access: ON** (the default; leave it)
5. Default encryption: **SSE-S3** (default)
6. Create. Note the bucket name.

## 2. IAM — role for the EC2 server

The app never stores AWS keys. EC2 gets temporary credentials from this role.

1. **IAM → Policies → Create policy → JSON**, paste `deploy/iam-s3-policy.json`,
   replace `YOUR-BUCKET-NAME` with your bucket name. Name it `ResultCloudS3Marksheets`.
   (This allows only put/get on `marksheets/*` in that one bucket: least privilege.)
2. **IAM → Roles → Create role**
   - Trusted entity: **AWS service → EC2**
   - Permissions: `ResultCloudS3Marksheets` and `CloudWatchAgentServerPolicy`
   - Name: `ResultCloud-EC2-Role`

## 3. Security groups (firewalls)

**EC2 → Security Groups → Create security group** (default VPC):

| Name | Inbound rules |
|---|---|
| `resultcloud-web-sg` | HTTP 80 from `0.0.0.0/0`, SSH 22 from **My IP** |
| `resultcloud-db-sg` | MySQL/Aurora 3306 from source **`resultcloud-web-sg`** |

So the database accepts connections only from the web server, never from the internet.

## 4. RDS — MySQL database

1. **RDS → Create database → Standard create**
2. Engine: **MySQL** 8.0, Template: **Free tier**
3. DB instance identifier: `resultcloud-db`
4. Master username: `admin`, set a strong password (save it)
5. Instance: `db.t4g.micro` (or `db.t3.micro`), Storage 20 GB
6. Connectivity: default VPC, **Public access: No**, security group: `resultcloud-db-sg` (remove `default`)
7. **Additional configuration → Initial database name: `resultcloud`**
8. Create, wait until status is **Available** (about 10 minutes), then copy the **Endpoint**.

## 5. EC2 — the web server

1. **EC2 → Launch instance**
2. Name `resultcloud-web`, AMI **Amazon Linux 2023**, type `t3.micro` (or `t2.micro`)
3. Key pair: create one (download the `.pem`; never commit it)
4. Network: security group `resultcloud-web-sg`
5. **Advanced details → IAM instance profile: `ResultCloud-EC2-Role`**
6. Launch, then copy the **Public IPv4 address**.

## 6. Deploy the app on EC2

Connect: **EC2 → instance → Connect → EC2 Instance Connect → Connect** (opens a browser terminal).

```bash
sudo dnf install -y git
git clone https://github.com/<your-username>/ResultCloud.git
cd ResultCloud
cp .env.example .env
nano .env
```

Fill in `.env`:

```
DB_HOST=<RDS endpoint>
DB_PORT=3306
DB_NAME=resultcloud
DB_USER=admin
DB_PASSWORD=<RDS password>
S3_BUCKET=<bucket name>
AWS_REGION=ap-south-1
SECRET_KEY=<long random string: python3 -c "import secrets;print(secrets.token_hex(32))">
ADMIN_PASSWORD=<admin login password, 8+ chars>
LOG_FILE=/var/log/resultcloud/app.log
HTTPS=0
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`), then run the setup:

```bash
bash deploy/setup_ec2.sh
```

It installs Python, Nginx and the CloudWatch agent, builds the React app, creates the tables in RDS,
creates the `admin` user and starts everything. Open `http://<EC2 public IP>/` and log in as **Admin**
with `admin` / your `ADMIN_PASSWORD`. Then create faculty and students from the Admin portal.

Later code updates: `bash deploy/update.sh`.

Check it is healthy: `curl http://localhost/api/health` → `{"status":"ok"}` (this also tests the RDS connection).

## 7. CloudWatch — monitoring and logs

The setup script already started the CloudWatch agent with `deploy/cloudwatch-agent.json`.

- **Logs:** CloudWatch → Log groups → `resultcloud-app` (logins, failed logins, S3 uploads, errors with
  stack traces), `resultcloud-nginx-access`, `resultcloud-nginx-error`.
- **Metrics:** EC2 CPU and status checks are automatic. The agent adds memory and disk under the custom
  namespace `ResultCloud`.
- **Alarm:** CloudWatch → Alarms → Create alarm → EC2 → Per-Instance → `CPUUtilization` for
  `resultcloud-web` → Greater than 70 for 5 minutes. Add a second alarm on `StatusCheckFailed` ≥ 1.
- **Dashboard:** CloudWatch → Dashboards → Create `ResultCloud` with CPUUtilization, StatusCheckFailed,
  `mem_used_percent` and a Logs widget on `resultcloud-app` filtered to `ERROR`.

## 8. Test the whole system

1. Admin: create a faculty user and a student (SAP ID decides department and grading scale).
2. Faculty: Enter Marks → Save & Calculate → Publish result.
3. Student: Results → Download PDF → the file appears in S3 under `marksheets/<sap id>/`
   (Admin → Results also shows the S3 key).
4. CloudWatch: the login and upload lines show up in `resultcloud-app`.
5. RDS: data survives `sudo systemctl restart resultcloud`.

## 9. Stop charges after the demo

Stop or terminate the EC2 instance, delete the RDS database (untick final snapshot if not needed),
and empty and delete the S3 bucket.

## Security summary

| Area | How |
|---|---|
| AWS credentials | EC2 IAM role only; no keys in code, `.env` or GitHub |
| S3 | private bucket, public access blocked, SSE-S3 encryption, role limited to `marksheets/*` |
| RDS | not publicly accessible; port 3306 open only to the web server's security group |
| EC2 | only port 80 public; SSH only from your IP |
| App | hashed passwords, HttpOnly session cookie, role checks on every API route, JSON-only writes (CSRF), SQLAlchemy parameterised queries, input validation |
