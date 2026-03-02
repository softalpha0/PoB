# Proof of Belief (PoB) Bot

A Discord bot designed to verify community contributions and manage rewards within the Spicenet ecosystem.

### 🚀 Features
* **Multimedia Submissions**: Support for screenshots, videos, and links across all categories.
* **Smart Verification**: Specialized logic for **Community Spaces** (min. 20 attendees required).
* **Automated Security**: A "3-Strike" system that automatically blacklists bad actors.
* **Persistence**: SQLite3 database tracking for Belief Credits (BC) and strikes.

### 🛠️ Commands
* `/submit`: Upload proof for Engagement, Bug Reports, Content, or Spaces.
* `/profile`: Privately check your own BC balance and strike count.
* `/leaderboard`: See the top 10 Believers.
* `/pardon`: (Admin Only) Clear strikes or un-blacklist a user.

### 📋 Submission Categories
| Category | Reward | Requirement |
| :--- | :--- | :--- |
| Engagement | 5 BC | community activites interaction  |
| Bug Report | 15 BC | Verified technical issues |
| Content | 20 BC | High-quality media/threads |
| Community Spaces | 25 BC | 20+ attendees + Recap |

