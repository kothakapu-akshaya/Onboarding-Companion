Create a step-by-step plan for a backend app using fastapi. These are the requirements.

1. User authentication. User will use phone number to create and account or login if already exists. User will login only one time. Every other time frontend will check and authenticate automatically.
2. Roles. For now there are 2 roles (admin, users)
    1. Fields for user/admin
        - Name, Phone, email, Gender, DoB, Place
3. Cateogries (Default categories). Admin can add or remove
    1. Fields
        - Name, Title, Description, Published, Rank, Data Record (backref)
4. Record which can have text, audio, video, image. Linked with user and category
    1. Fields
        - UID, Type, User (backref), Category (reference), Geo tag, storage path/link
5. Data is stored in minio buckets the details of the bucket, file name should be linked with record. The file should have the same UID of the record.
6. Add a check to see if the record is saved to the bucket and send a notification back. If the upload fails or retry is needed save these states. the frontend will periodically check for the state and retry to call upload to upload the pending records.

Once the plan is ready break the tasks into user stories. Make sure to create user stories as small as possible it is ok to have more stories with simple tasks.

Suggest if any fields or tables have to be added.