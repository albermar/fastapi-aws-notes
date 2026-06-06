import boto3

BUCKET = 'mi-app-documents-martin'

s3 = boto3.client('s3')

#delete all files:
response = s3.list_objects_v2(Bucket=BUCKET)
for obj in response.get("Contents", []):
    s3.delete_object(Bucket=BUCKET, Key=obj['Key'])
    

#upload
s3.put_object(Bucket=BUCKET, Key='test/hello.txt', Body=b"Hello world")

#list
response = s3.list_objects_v2(Bucket=BUCKET)

for obj in response.get("Contents", []):
    print(obj['Key'])
    
#read without download
obj = s3.get_object(Bucket=BUCKET, Key="test/hello.txt")
print(obj["Body"].read().decode("utf-8"))

# delete
s3.delete_object(Bucket=BUCKET, Key="test/hello.txt")