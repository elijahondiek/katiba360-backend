import asyncio
import asyncpg
import os

async def add_column():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    try:
        await conn.execute('ALTER TABLE tbl_users ADD COLUMN bio VARCHAR(500)')
        print('Successfully added bio column')
    except Exception as e:
        if 'already exists' in str(e):
            print('Bio column already exists')
        else:
            print(f'Error: {e}')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_column())