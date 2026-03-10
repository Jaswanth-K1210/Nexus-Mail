# How to Migrate Nexus Mail to MongoDB Atlas

This guide walks you through the exact steps to transition your local Nexus Mail instance (`mongodb://localhost:27017`) to a globally distributed, cloud-hosted **MongoDB Atlas** database.

This is a critical step for deploying the open-source architecture to production.

## Step 1: Create a Free MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and sign up for a free account.
2. Under "Deploy a Database", select the **M0 Free** tier.
3. Choose a provider (AWS, Google Cloud, or Azure) and a region closest to your users.
4. Click **Create Deployment**.

## Step 2: Configure Database Security

You must configure two security settings before you can connect to your new cloud database:

### A. Create a Database User
1. In the Atlas dashboard, navigate to **Database Access** (on the left sidebar).
2. Click **+ Add New Database User**.
3. Choose **Password** for the Authentication Method.
4. Create a secure username (e.g., `nexus_admin`) and click **Autogenerate Secure Password**.
   * **CRITICAL:** Copy this password and save it somewhere immediately. You will need it in Step 4.
5. Under Database User Privileges, select **Read and write to any database**.
6. Click **Add User**.

### B. Allow Network Access (IP Whitelisting)
By default, Atlas blocks all incoming connections. You must allow your backend server to connect.
1. Navigate to **Network Access** (on the left sidebar).
2. Click **+ Add IP Address**.
3. To allow connections from anywhere (necessary if you are deploying to Render/Vercel/AWS without static IPs), click **ALLOW ACCESS FROM ANYWHERE** (`0.0.0.0/0`).
    * *Note: For strict production environments, you would only whitelist your specific backend server's IP address.*
4. Click **Confirm**.

## Step 3: Get Your Connection String

1. Navigate to your **Database** clusters overview (on the left sidebar).
2. Click the **Connect** button next to your Cluster0.
3. Select **Drivers**.
4. Make sure **Python** is selected as the Driver, and the Version is **3.6 or later**.
5. Copy the connection string provided. It will look something like this:
   `mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0`

## Step 4: Update Your Local `.env` File

1. Open your Nexus Mail project in your editor.
2. Locate the `.env` file inside the `/backend` folder.
3. Find the `MONGODB_URI` line. (It currently says `mongodb://localhost:27017`).
4. Replace it with the string you copied from Atlas.
5. **CRITICAL:** Inside the string, manually replace `<username>` with the username you created (e.g., `nexus_admin`) and `<password>` with the secure password you copied earlier.

It should look exactly like this:
```env
# /backend/.env
MONGODB_URI="mongodb+srv://nexus_admin:YourSuperSecretPassword123!@cluster0.xxxxx.mongodb.net/nexus_mail?retryWrites=true&w=majority&appName=Cluster0"
MONGODB_DATABASE="nexus_mail"
```
*(Notice we added `nexus_mail` before the `?` to specify the default database name).*

## Step 5: Restart the Backend

That's it! Because Nexus Mail uses async `motor`, it automatically understands Atlas connection strings.

1. Stop your currently running backend server (`Ctrl+C`).
2. Restart it:
   ```bash
   source .venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Look at your terminal startup logs. You should see:
   `[info     ] Connecting to MongoDB          uri=mongodb+srv://...`
   `[info     ] MongoDB connected              database=nexus_mail`

The backend will automatically start building the `users`, `emails`, `rules`, and `drafts` collections in the cloud. The 30-Day TTL privacy indexes will be rebuilt on Atlas automatically within seconds.
