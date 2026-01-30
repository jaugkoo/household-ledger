# Azure App Registration Guide

Follow these steps to create a Microsoft Azure app and get the credentials needed for OneDrive API access.

## Step 1: Access Azure Portal

1. Go to [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account (same account as OneDrive)

## Step 2: Register a New Application

1. Search for **"Microsoft Entra ID"** (formerly Azure Active Directory) in the top search bar
2. Click **"App registrations"** in the left menu
3. Click **"+ New registration"**

### Fill in the form:
- **Name**: `Receipt Automation`
- **Supported account types**: Select **"Accounts in any organizational directory and personal Microsoft accounts"**
- **Redirect URI**: Leave blank for now
- Click **"Register"**

## Step 3: Get Application (Client) ID and Tenant ID

After registration, you'll see the app overview page.

**Copy these values:**
- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

Save these for later.

## Step 4: Create a Client Secret

1. In the left menu, click **"Certificates & secrets"**
2. Click **"+ New client secret"**
3. **Description**: `Receipt Automation Secret`
4. **Expires**: Select **24 months**
5. Click **"Add"**

**IMPORTANT:** Copy the **"Value"** immediately (it will only be shown once!)
- **Client Secret Value**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 5: Grant API Permissions

1. In the left menu, click **"API permissions"**
2. Click **"+ Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Delegated permissions"**
5. Search and check:
   - `Files.Read`
   - `Files.Read.All`
   - `offline_access`
6. Click **"Add permissions"**

## Step 6: Generate Refresh Token

We need to authenticate once to get a refresh token.

### Option A: Use Browser (Easier)

1. Open this URL in your browser (replace `YOUR_CLIENT_ID`):
   ```
   https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&response_mode=query&scope=Files.Read.All%20offline_access
   ```

2. Sign in and grant permissions
3. You'll be redirected to `http://localhost/?code=XXXXX`
4. Copy the **code** from the URL

5. Run this command (replace placeholders):
   ```powershell
   curl -X POST https://login.microsoftonline.com/common/oauth2/v2.0/token -d "client_id=YOUR_CLIENT_ID&scope=Files.Read.All offline_access&code=YOUR_CODE&redirect_uri=http://localhost&grant_type=authorization_code&client_secret=YOUR_CLIENT_SECRET"
   ```

6. Copy the **refresh_token** from the response

### Option B: I'll create a helper script for you

Let me know if you want me to create a Python script to automate this step.

## Summary

You should now have:
- ✅ Client ID
- ✅ Client Secret
- ✅ Tenant ID
- ✅ Refresh Token

Save these values - we'll add them to `.env` in the next step!
