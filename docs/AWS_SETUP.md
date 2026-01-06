# AWS Setup Guide for CloudShift

This guide walks you through setting up AWS resources required for CloudShift.

## Prerequisites

- AWS Account
- AWS CLI installed and configured (optional but recommended)

## 1. Create S3 Bucket

### Option A: Using AWS Console

1. Go to [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Click "Create bucket"
3. Configure bucket:
   - **Bucket name**: `cloudshift-intermediate-<your-unique-id>` (must be globally unique)
   - **Region**: Choose your preferred region (e.g., `us-east-1`)
   - **Block Public Access**: Keep all options ENABLED (bucket should not be public)
   - **Bucket Versioning**: Disabled
   - **Default encryption**: Enable with `Amazon S3-managed keys (SSE-S3)`
4. Click "Create bucket"

### Option B: Using AWS CLI

```bash
# Set your bucket name
BUCKET_NAME="cloudshift-intermediate-$(date +%s)"
AWS_REGION="us-east-1"

# Create bucket
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION \
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable server-side encryption
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

# Block public access
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "Bucket created: $BUCKET_NAME"
```

## 2. Configure Lifecycle Policy (Optional but Recommended)

To automatically delete intermediate files after 7 days:

### Using AWS Console

1. Go to your bucket
2. Click "Management" tab
3. Click "Create lifecycle rule"
4. Configure:
   - **Rule name**: `delete-old-files`
   - **Rule scope**: Apply to all objects
   - **Lifecycle rule actions**: Check "Expire current versions of objects"
   - **Days after object creation**: 7
5. Click "Create rule"

### Using AWS CLI

```bash
aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME \
    --lifecycle-configuration '{
        "Rules": [{
            "Id": "delete-old-files",
            "Status": "Enabled",
            "Expiration": {
                "Days": 7
            }
        }]
    }'
```

## 3. Create IAM User with Minimal Permissions

### Create IAM Policy

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Click "Policies" → "Create policy"
3. Click "JSON" tab and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CloudShiftS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::cloudshift-intermediate-*",
                "arn:aws:s3:::cloudshift-intermediate-*/*"
            ]
        }
    ]
}
```

4. Click "Next"
5. **Policy name**: `CloudShiftS3Policy`
6. Click "Create policy"

### Create IAM User

1. Go to "Users" → "Create user"
2. **User name**: `cloudshift-app`
3. Click "Next"
4. **Permissions**: Attach `CloudShiftS3Policy` directly
5. Click "Next" → "Create user"
6. Click on the created user → "Security credentials" tab
7. Click "Create access key"
8. **Use case**: Application running outside AWS
9. Click "Next" → "Create access key"
10. **IMPORTANT**: Copy the Access Key ID and Secret Access Key
    - These will only be shown once!

## 4. Configure CloudShift Backend

Add the following to your `backend/.env` file:

```env
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=cloudshift-intermediate-your-unique-id
```

## 5. Set Up AWS SES for Email Notifications (Optional)

### Verify Sender Email

1. Go to [SES Console](https://console.aws.amazon.com/ses/)
2. Click "Verified identities" → "Create identity"
3. **Identity type**: Email address
4. **Email address**: your-noreply@example.com
5. Click "Create identity"
6. Check your email and click the verification link

### Get SES Credentials

If you're in the SES sandbox (new accounts), you can only send to verified email addresses.

To send to any email:
1. Click "Account dashboard" → "Request production access"
2. Fill out the form explaining your use case

Add to `backend/.env`:

```env
SES_SENDER_EMAIL=your-noreply@example.com
```

## 6. Configure CORS (if using presigned URLs)

If you plan to use presigned URLs for direct browser uploads/downloads:

```bash
aws s3api put-bucket-cors \
    --bucket $BUCKET_NAME \
    --cors-configuration '{
        "CORSRules": [{
            "AllowedOrigins": ["http://localhost:3000", "https://your-domain.com"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 3000
        }]
    }'
```

## Security Best Practices

1. **Never commit AWS credentials** to version control
2. **Use IAM roles** instead of access keys when running on AWS infrastructure
3. **Rotate access keys** regularly (every 90 days)
4. **Enable CloudTrail** logging for S3 bucket to track access
5. **Use VPC endpoints** for S3 access if running on EC2 (reduces costs and improves security)
6. **Monitor S3 costs** - set up billing alerts in AWS Console

## Testing the Setup

From your backend directory:

```bash
source venv/bin/activate
python -c "
from app.services.s3 import s3_service
import io

# Test upload
test_data = b'Hello from CloudShift!'
s3_service.upload_file(io.BytesIO(test_data), 'test/hello.txt')

# Test file exists
exists = s3_service.file_exists('test/hello.txt')
print(f'File exists: {exists}')

# Test download
downloaded = io.BytesIO()
s3_service.download_file('test/hello.txt', downloaded)
print(f'Downloaded: {downloaded.getvalue().decode()}')

# Test delete
s3_service.delete_file('test/hello.txt')
print('File deleted')
"
```

## Troubleshooting

### Access Denied Error

- Verify IAM policy is attached to the user
- Check bucket name matches in policy and `.env`
- Verify access keys are correct

### Bucket Not Found

- Check bucket name spelling
- Verify region matches in CLI/Console and `.env`

### Encryption Errors

- Ensure bucket has default encryption enabled
- Check IAM policy includes necessary encryption permissions

## Cost Estimation

- **S3 Storage**: ~$0.023 per GB per month
- **Data Transfer OUT**: ~$0.09 per GB (first 10 TB)
- **Requests**: PUT/POST ~$0.005 per 1000, GET ~$0.0004 per 1000
- **SES**: $0.10 per 1000 emails

For a typical migration of 100 GB:
- Storage (1 week): ~$0.01
- Uploads/Downloads: ~$0.02
- **Estimated cost**: < $0.05 per 100 GB migration

Since files are deleted immediately after transfer, storage costs are minimal.
