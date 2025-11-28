import random
import string
from datetime import datetime, timedelta
from database.database import user_data, add_user, present_user

class ReferralSystem:
    def __init__(self):
        self.users = user_data
        print("✅ ReferralSystem initialized")
    
    def generate_referral_code(self):
        """Unique referral code generate karega"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    async def get_or_create_referral_code(self, user_id):
        """User ka referral code get/set karega"""
        try:
            # Pehle check karen user database mein hai ya nahi
            if not await present_user(user_id):
                await add_user(user_id)
                print(f"✅ User {user_id} added to database")
            
            user = await self.users.find_one({"_id": user_id})
            
            if user and user.get('referral_code'):
                return user['referral_code']
            
            # Naya code generate karen
            new_code = self.generate_referral_code()
            
            await self.users.update_one(
                {"_id": user_id},
                {"$set": {"referral_code": new_code}},
                upsert=True
            )
            print(f"✅ Referral code generated: {new_code} for user: {user_id}")
            return new_code
            
        except Exception as e:
            print(f"❌ Error in get_or_create_referral_code: {e}")
            return "REF123"
    
    async def give_premium(self, user_id, days):
        """User ko premium access den"""
        try:
            user = await self.users.find_one({"_id": user_id})
            current_expiry = user.get('free_premium_expiry') if user else None
            
            if current_expiry and current_expiry > datetime.now():
                # Existing premium hai, extend karen
                new_expiry = current_expiry + timedelta(days=days)
            else:
                # Naya premium den
                new_expiry = datetime.now() + timedelta(days=days)
            
            await self.users.update_one(
                {"_id": user_id},
                {"$set": {"free_premium_expiry": new_expiry}}
            )
            print(f"🎁 {days} days premium given to user {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error giving premium: {e}")
            return False
    
    async def is_new_user(self, user_id):
        """Check kare user naya hai ya existing"""
        try:
            user = await self.users.find_one({"_id": user_id})
            if not user:
                return True  # Naya user
            
            # Check karen user ne pehle kabhi file access li hai ya nahi
            # Agar user ke paas referred_by field nahi hai, toh existing user hai
            if user.get('referred_by') is None:
                # Check karen user ne kabhi file access li hai
                user_join_time = user.get('joined_at', datetime.now())
                time_since_join = datetime.now() - user_join_time
                
                # Agar user 1 hour se zyada purana hai, toh existing user consider karen
                if time_since_join > timedelta(hours=1):
                    return False  # Existing user
                return True  # Naya user (1 hour ke andar join kiya)
            
            return False  # Already referred ho chuka hai
        except Exception as e:
            print(f"❌ Error checking new user: {e}")
            return True
    
    async def process_referral(self, new_user_id, referral_code, username, bot):
        """Referral process handle karega - SIRF NEW USERS KE LIYE"""
        try:
            print(f"🔄 Processing referral: New User: {new_user_id}, Code: {referral_code}")
            
            # ✅ PEHLE CHECK KAREN USER NEW HAI YA EXISTING
            is_new = await self.is_new_user(new_user_id)
            
            if not is_new:
                print(f"❌ User {new_user_id} is EXISTING USER - No referral reward")
                await bot.send_message(
                    new_user_id,
                    "ℹ️ **Existing User Detected**\n\n"
                    "Referral rewards are only for new users who join via your link. "
                    "Since you were already using the bot, no premium was activated.\n\n"
                    "But thanks for sharing! 🚀"
                )
                return False
            
            # Pehle ensure karen new user database mein hai
            if not await present_user(new_user_id):
                await add_user(new_user_id)
                print(f"✅ New user {new_user_id} added to database during referral")
            
            # Referrer find karen
            referrer = await self.users.find_one({"referral_code": referral_code})
            
            if not referrer:
                print(f"❌ Referrer not found for code: {referral_code}")
                return False
            
            if referrer['_id'] == new_user_id:
                print("❌ Self-referral detected!")
                return False
            
            # Check if already referred
            existing_user = await self.users.find_one({"_id": new_user_id})
            if existing_user and existing_user.get('referred_by'):
                print("✅ User already referred by someone")
                return True
            
            print(f"🎯 Referrer found: {referrer['_id']}")
            
            # ✅ NEW USER KO 1 DAY PREMIUM DEN
            await self.give_premium(new_user_id, 1)
            
            # ✅ REFERRER KO CUMULATIVE PREMIUM DEN (1 DAY per referral)
            current_count = referrer.get('referral_count', 0)
            new_count = current_count + 1
            
            # Referrer ko cumulative premium den (1 referral = 1 day, 2 referrals = 2 days, etc.)
            await self.give_premium(referrer['_id'], new_count)
            
            # Update referrer count and referred_by
            await self.users.update_one(
                {"_id": referrer['_id']},
                {"$set": {"referral_count": new_count}}
            )
            
            await self.users.update_one(
                {"_id": new_user_id},
                {"$set": {"referred_by": referrer['_id']}}
            )
            
            print(f"✅ Referral count updated: {current_count} -> {new_count}")
            print(f"🎁 Rewards: New user got 1 day, Referrer got {new_count} days premium")
            
            # Send notifications
            await self.send_referral_notifications(referrer['_id'], new_user_id, new_count, bot)
            
            print("🎉 Referral processing completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error in process_referral: {e}")
            return False
    
    async def send_referral_notifications(self, referrer_id, new_user_id, new_count, bot):
        """Donon users ko notification bhejega"""
        try:
            print(f"📨 Sending notifications...")
            
            total_days = new_count
            
            # Referrer notification
            await bot.send_message(
                referrer_id,
                f"🎉 **New Referral!**\n\n"
                f"✅ New user joined using your link!\n"
                f"📊 Total referrals: {new_count}\n"
                f"🎯 You earned: {total_days} days premium!\n\n"
                f"Keep sharing your link! 🚀"
            )
            
            # New user notification
            await bot.send_message(
                new_user_id,
                f"🎁 **Welcome! FREE PREMIUM ACTIVATED**\n\n"
                f"✅ 1 DAY FREE PREMIUM activated!\n"
                f"⚡ No token verification for 24 hours\n"
                f"📤 Direct file access enabled\n\n"
                f"Use /myrefer to share your own link and earn more rewards! 🔗"
            )
            
            print("✅ Notifications sent successfully!")
            
        except Exception as e:
            print(f"❌ Notification error: {e}")
    
    async def get_referral_stats(self, user_id):
        """User ka referral stats return karega"""
        try:
            print(f"📊 Getting stats for user: {user_id}")
            
            if not await present_user(user_id):
                await add_user(user_id)
                print(f"✅ User {user_id} added to database")
            
            user = await self.users.find_one({"_id": user_id})
            
            if not user:
                return None
            
            referral_count = user.get('referral_count', 0)
            referral_code = await self.get_or_create_referral_code(user_id)
            
            # Premium status check
            has_premium = False
            premium_till = None
            
            if user.get('free_premium_expiry') and user['free_premium_expiry'] > datetime.now():
                has_premium = True
                premium_till = user['free_premium_expiry']
            
            stats = {
                'referral_count': referral_count,
                'referral_code': referral_code,
                'has_premium': has_premium,
                'premium_till': premium_till
            }
            
            print(f"✅ Stats generated for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            print(f"❌ Error in get_referral_stats: {e}")
            return None
    
    async def check_premium_access(self, user_id):
        """Check kare user ko premium access hai ya nahi"""
        try:
            user = await self.users.find_one({"_id": user_id})
            if not user:
                return False
            
            if user.get('free_premium_expiry') and user['free_premium_expiry'] > datetime.now():
                return True
            
            return False
        except Exception as e:
            print(f"❌ Error checking premium: {e}")
            return False

# ✅ Global instance
referral_manager = ReferralSystem()