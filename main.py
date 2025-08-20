import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import json
import datetime
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)

# File paths
PLAYER_DATA_FILE = 'player_data.json'
BLACKJACK_DATA_FILE = 'blackjack_data.json'

# --- Split hand tracking ---
split_hands = {}
split_in_progress = set()

# Helper function to draw a card from the deck
def draw_card():
    deck = create_deck()
    return random.choice(deck)

# Load player data
def load_player_data():
    try:
        with open(PLAYER_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save player data
def save_player_data(data):
    with open(PLAYER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load blackjack data
def load_blackjack_data():
    try:
        with open(BLACKJACK_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save blackjack data
def save_blackjack_data(data):
    with open(BLACKJACK_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Card deck
def create_deck():
    # Using actual card emojis
    deck = [
        # Spades (♠️)
        '🂡', '🂢', '🂣', '🂤', '🂥', '🂦', '🂧', '🂨', '🂩', '🂪', '🂫', '🂭', '🂮',
        # Hearts (♥️)
        '🂱', '🂲', '🂳', '🂴', '🂵', '🂶', '🂷', '🂸', '🂹', '🂺', '🂻', '🂽', '🂾',
        # Diamonds (♦️)
        '🃁', '🃂', '🃃', '🃄', '🃅', '🃆', '🃇', '🃈', '🃉', '🃊', '🃋', '🃍', '🃎',
        # Clubs (♣️)
        '🃑', '🃒', '🃓', '🃔', '🃕', '🃖', '🃗', '🃘', '🃙', '🃚', '🃛', '🃝', '🃞'
    ]
    return deck

# Calculate score
def calculate_score(hand):
    score = 0
    aces = 0

    # Card emoji to value mapping
    card_values = {
        # Spades
        '🂡': 1, '🂢': 2, '🂣': 3, '🂤': 4, '🂥': 5, '🂦': 6, '🂧': 7, '🂨': 8, '🂩': 9, '🂪': 10, '🂫': 10, '🂭': 10, '🂮': 10,
        # Hearts  
        '🂱': 1, '🂲': 2, '🂳': 3, '🂴': 4, '🂵': 5, '🂶': 6, '🂷': 7, '🂸': 8, '🂹': 9, '🂺': 10, '🂻': 10, '🂽': 10, '🂾': 10,
        # Diamonds
        '🃁': 1, '🃂': 2, '🃃': 3, '🃄': 4, '🃅': 5, '🃆': 6, '🃇': 7, '🃈': 8, '🃉': 9, '🃊': 10, '🃋': 10, '🃍': 10, '🃎': 10,
        # Clubs
        '🃑': 1, '🃒': 2, '🃓': 3, '🃔': 4, '🃕': 5, '🃖': 6, '🃗': 7, '🃘': 8, '🃙': 9, '🃚': 10, '🃛': 10, '🃝': 10, '🃞': 10
    }

    for card in hand:
        value = card_values.get(card, 0)

        if value == 1:  # Ace
            aces += 1
            score += 11
        else:
            score += value

    # Adjust for aces
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1

    return score

# Create blackjack embed
def create_blackjack_embed(username, player_hand, dealer_hand, player_total, show_dealer_total=False):
    embed = discord.Embed(
        title=f"🎰 {username}'s Blackjack Table 🎰",
        color=discord.Color.dark_red()
    )

    # Player hand
    player_cards = ''.join(player_hand)
    embed.add_field(name="👤 Player Hand", value=f"{player_cards} ({player_total})", inline=False)

    # Dealer hand
    if show_dealer_total:
        dealer_cards = ''.join(dealer_hand)
        dealer_value = f"({calculate_score(dealer_hand)})"
    else:
        dealer_cards = f"{dealer_hand[0]} ❓"
        visible_card_value = calculate_score([dealer_hand[0]])
        dealer_value = f"({visible_card_value} + ?)"

    embed.add_field(name="🏛️ Dealer Hand", value=f"{dealer_cards} {dealer_value}", inline=False)

    return embed

# Game class
class BlackjackGame:
    def __init__(self, user_id, bet_amount=50):
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.deck = create_deck()

        # Multiple shuffles for better randomization
        for _ in range(5):
            random.shuffle(self.deck)

        # Use random.SystemRandom for better entropy if available
        try:
            secure_random = random.SystemRandom()
            secure_random.shuffle(self.deck)
        except:
            pass  # Fall back to regular random if SystemRandom unavailable

        self.player_hand = []
        self.dealer_hand = []

        # Deal initial cards
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())

        self.game_over = False
        self.doubled_down = False

    def can_double_down(self):
        return len(self.player_hand) == 2 and not self.doubled_down

    def hit(self):
        if not self.game_over:
            self.player_hand.append(self.deck.pop())
            if calculate_score(self.player_hand) > 21:
                self.game_over = True
                return "bust"
        return "continue"

    def double_down(self):
        if self.can_double_down():
            self.doubled_down = True
            self.bet_amount *= 2
            self.hit()
            self.game_over = True
            return True
        return False

    def dealer_play(self):
        while calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

    def get_result(self):
        player_score = calculate_score(self.player_hand)
        dealer_score = calculate_score(self.dealer_hand)

        if player_score > 21:
            return "player_bust"
        elif dealer_score > 21:
            return "dealer_bust"
        elif player_score == 21 and len(self.player_hand) == 2:
            if dealer_score == 21 and len(self.dealer_hand) == 2:
                return "push"
            return "blackjack"
        elif dealer_score == 21 and len(self.dealer_hand) == 2:
            return "dealer_blackjack"
        elif player_score > dealer_score:
            return "player_wins"
        elif dealer_score > player_score:
            return "dealer_wins"
        else:
            return "push"

# Active games storage
active_games = {}

# Bet selection buttons
class BetButton(discord.ui.Button):
    def __init__(self, bet_amount):
        super().__init__(label=f"{bet_amount} Chips", style=discord.ButtonStyle.primary)
        self.bet_amount = bet_amount

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Check if user already has an active game
        if interaction.user.id in active_games:
            await interaction.response.send_message("You already have an active blackjack game!", ephemeral=True)
            return

        # Load player data
        player_data = load_player_data()

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}
            save_player_data(player_data)

        # Check if player has enough chips
        if player_data[user_id]["chips"] < self.bet_amount:
            await interaction.response.send_message(f"You don't have enough chips! You have {player_data[user_id]['chips']} chips.", ephemeral=True)
            return

        # Deduct bet from player chips
        player_data[user_id]["chips"] -= self.bet_amount
        save_player_data(player_data)

        # Create new game
        game = BlackjackGame(interaction.user.id, self.bet_amount)
        active_games[interaction.user.id] = game

        player_total = calculate_score(game.player_hand)

        # Check for immediate blackjack
        if player_total == 21:
            dealer_total = calculate_score(game.dealer_hand)
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total,
                show_dealer_total=True
            )

            # Update blackjack data first
            blackjack_data = load_blackjack_data()
            if user_id not in blackjack_data:
                blackjack_data[user_id] = {"wins": 0, "losses": 0}

            if dealer_total == 21:
                embed.color = discord.Color.orange()
                embed.set_footer(text="🤝 Both have blackjack! It's a tie!")
                player_data[user_id]["chips"] += self.bet_amount  # Refund bet - no win/loss recorded
            else:
                embed.color = discord.Color.green()
                embed.set_footer(text="🃏 BLACKJACK! You win!")
                player_data[user_id]["chips"] += int(self.bet_amount * 2.5)  # 1.5x profit + original bet
                player_data[user_id]["wins"] += 1
                blackjack_data[user_id]["wins"] += 1

            save_blackjack_data(blackjack_data)
            save_player_data(player_data)
            del active_games[interaction.user.id]

            # Show end game message with rematch button
            game_data = {
                'player_hand': game.player_hand.copy(),
                'dealer_hand': game.dealer_hand.copy()
            }
            if dealer_total == 21:
                await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", self.bet_amount, game_data, self.bet_amount)
            else:
                await end_blackjack_game(interaction, interaction.user, None, "win", self.bet_amount, game_data, self.bet_amount)
        else:
            # Normal game start
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total
            )

            view = BlackjackButtonView(game)
            await interaction.response.edit_message(embed=embed, view=view)

class BetSelectionView(discord.ui.View):
    def __init__(self, user_chips):
        super().__init__(timeout=300)
                    

        # Add bet buttons based on available chips
        if user_chips >= 25:
            self.add_item(BetButton(25))
        if user_chips >= 50:
            self.add_item(BetButton(50))
        if user_chips >= 100:
            self.add_item(BetButton(100))

# Button classes
class HitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Hit", style=discord.ButtonStyle.primary, emoji="🟦", row=0)

    async def callback(self, interaction: discord.Interaction):
        game = active_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("No active game found!", ephemeral=True)
            return

        result = game.hit()
        player_total = calculate_score(game.player_hand)

        if result == "bust":
            # Player busted
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total,
                show_dealer_total=True
            )
            embed.color = discord.Color.red()
            embed.set_footer(text="💥 BUST! You went over 21!")

            # Update player data
            player_data = load_player_data()
            user_id = str(interaction.user.id)

            if user_id not in player_data:
                player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

            player_data[user_id]["losses"] += 1
            save_player_data(player_data)

            # Update blackjack data
            blackjack_data = load_blackjack_data()
            if user_id not in blackjack_data:
                blackjack_data[user_id] = {"wins": 0, "losses": 0}
            blackjack_data[user_id]["losses"] += 1
            save_blackjack_data(blackjack_data)

            # Save game data before deleting
            game_data = {
                'player_hand': game.player_hand.copy(),
                'dealer_hand': game.dealer_hand.copy()
            }
            del active_games[interaction.user.id]

            # Show end game message
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, game.bet_amount)
        else:
            # Continue game
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total
            )

            view = BlackjackButtonView(game)
            await interaction.response.edit_message(embed=embed, view=view)

class StandButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋", row=0)

    async def callback(self, interaction: discord.Interaction):
        game = active_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("No active game found!", ephemeral=True)
            return

        # Dealer plays
        game.dealer_play()
        game.game_over = True

        result = game.get_result()
        player_total = calculate_score(game.player_hand)
        dealer_total = calculate_score(game.dealer_hand)

        embed = create_blackjack_embed(
            interaction.user.display_name,
            game.player_hand,
            game.dealer_hand,
            player_total,
            show_dealer_total=True
        )

        # Update player data
        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        # Update blackjack data
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}

        if result in ["player_wins", "dealer_bust", "blackjack"]:
            embed.color = discord.Color.green()
            if result == "blackjack":
                embed.set_footer(text="🃏 BLACKJACK! You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2.5)  # 1.5x profit + original bet
            elif result == "dealer_bust":
                embed.set_footer(text="💥 Dealer busted! You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2)  # 1x profit + original bet
            else:
                embed.set_footer(text="🎉 You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2)  # 1x profit + original bet

            player_data[user_id]["wins"] += 1
            blackjack_data[user_id]["wins"] += 1

        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            embed.color = discord.Color.red()
            if result == "dealer_blackjack":
                embed.set_footer(text="🃏 Dealer has blackjack! You lose!")
            else:
                embed.set_footer(text="😔 You lose!")

            player_data[user_id]["losses"] += 1
            blackjack_data[user_id]["losses"] += 1

        else:  # push
            embed.color = discord.Color.orange()
            embed.set_footer(text="🤝 It's a tie!")
            player_data[user_id]["chips"] += game.bet_amount

        save_player_data(player_data)
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message
        if result in ["player_wins", "dealer_bust", "blackjack"]:
            await end_blackjack_game(interaction, interaction.user, None, "win", game.bet_amount, game_data, game.bet_amount)
        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, game.bet_amount)
        else:  # push
            await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", game.bet_amount, game_data, game.bet_amount)

class ForfeitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Forfeit", style=discord.ButtonStyle.danger, emoji="🟥", row=0)

    async def callback(self, interaction: discord.Interaction):
        game = active_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("No active game found!", ephemeral=True)
            return

        player_total = calculate_score(game.player_hand)

        embed = create_blackjack_embed(
            interaction.user.display_name,
            game.player_hand,
            game.dealer_hand,
            player_total,
            show_dealer_total=True
        )
        embed.color = discord.Color.red()
        embed.set_footer(text="🏳️ You forfeited the game!")

        # Update player data
        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        player_data[user_id]["losses"] += 1
        save_player_data(player_data)

        # Update blackjack data
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}
        blackjack_data[user_id]["losses"] += 1
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message
        await end_blackjack_game(interaction, None, interaction.user, "forfeit", game.bet_amount, game_data, game.bet_amount)

class DoubleDownButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Double Down", style=discord.ButtonStyle.success, emoji="💰", row=0)

    async def callback(self, interaction: discord.Interaction):
        game = active_games.get(interaction.user.id)
        if not game:
            await interaction.response.send_message("No active game found!", ephemeral=True)
            return

        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        if player_data[user_id]["chips"] < game.bet_amount:
            await interaction.response.send_message("Not enough chips to double down!", ephemeral=True)
            return

        if not game.can_double_down():
            await interaction.response.send_message("Cannot double down at this time!", ephemeral=True)
            return

        # Deduct additional bet
        player_data[user_id]["chips"] -= game.bet_amount
        save_player_data(player_data)

        # Double down
        game.double_down()

        # Dealer plays
        game.dealer_play()

        result = game.get_result()
        player_total = calculate_score(game.player_hand)

        embed = create_blackjack_embed(
            interaction.user.display_name,
            game.player_hand,
            game.dealer_hand,
            player_total,
            show_dealer_total=True
        )

        # Update results
        player_data = load_player_data()
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}

        if result in ["player_wins", "dealer_bust", "blackjack"]:
            embed.color = discord.Color.green()
            embed.set_footer(text="🎉 Double down win!")
            player_data[user_id]["chips"] += int(game.bet_amount * 2)  # This is correct since bet was already doubled
            player_data[user_id]["wins"] += 1
            blackjack_data[user_id]["wins"] += 1

        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            embed.color = discord.Color.red()
            embed.set_footer(text="😔 Double down loss!")
            player_data[user_id]["losses"] += 1
            blackjack_data[user_id]["losses"] += 1

        else:  # push
            embed.color = discord.Color.orange()
            embed.set_footer(text="🤝 Double down tie!")
            player_data[user_id]["chips"] += game.bet_amount

        save_player_data(player_data)
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message
        original_bet = game.bet_amount // 2  # Get original bet before doubling
        if result in ["player_wins", "dealer_bust", "blackjack"]:
            await end_blackjack_game(interaction, interaction.user, None, "win", game.bet_amount, game_data, original_bet)
        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, original_bet)
        else:  # push
            await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", game.bet_amount, game_data, original_bet)

class BlackjackButtonView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=120)  # Increase timeout to 2 minutes
        self.game = game

        # Create buttons and bind callbacks - all buttons will be on row 0 by default
        hit_button = Button(label="Hit", style=discord.ButtonStyle.primary, custom_id="hit", emoji="🟦")
        hit_button.callback = self.hit_callback

        stand_button = Button(label="Stand", style=discord.ButtonStyle.secondary, custom_id="stand", emoji="✋")
        stand_button.callback = self.stand_callback

        forfeit_button = Button(label="Forfeit", style=discord.ButtonStyle.danger, custom_id="forfeit", emoji="🟥")
        forfeit_button.callback = self.forfeit_callback

        self.add_item(hit_button)
        self.add_item(stand_button)
        self.add_item(forfeit_button)

        if game.can_double_down():
            double_button = Button(label="Double Down", style=discord.ButtonStyle.success, custom_id="double", emoji="💰")
            double_button.callback = self.double_callback
            self.add_item(double_button)

        # Check if player can split (same rank cards)
        if len(game.player_hand) == 2:
            # Get card values for comparison
            card_values = {
                # Spades
                '🂡': 1, '🂢': 2, '🂣': 3, '🂤': 4, '🂥': 5, '🂦': 6, '🂧': 7, '🂨': 8, '🂩': 9, '🂪': 10, '🂫': 10, '🂭': 10, '🂮': 10,
                # Hearts  
                '🂱': 1, '🂲': 2, '🂳': 3, '🂴': 4, '🂵': 5, '🂶': 6, '🂷': 7, '🂸': 8, '🂹': 9, '🂺': 10, '🂻': 10, '🂽': 10, '🂾': 10,
                # Diamonds
                '🃁': 1, '🃂': 2, '🃃': 3, '🃄': 4, '🃅': 5, '🃆': 6, '🃇': 7, '🃈': 8, '🃉': 9, '🃊': 10, '🃋': 10, '🃍': 10, '🃎': 10,
                # Clubs
                '🃑': 1, '🃒': 2, '🃓': 3, '🃔': 4, '🃕': 5, '🃖': 6, '🃗': 7, '🃘': 8, '🃙': 9, '🃚': 10, '🃛': 10, '🃝': 10, '🃞': 10
            }

            card1_value = card_values.get(game.player_hand[0], 0)
            card2_value = card_values.get(game.player_hand[1], 0)

            if card1_value == card2_value:  # Same rank
                split_button = Button(label="Split", style=discord.ButtonStyle.blurple, custom_id="split", emoji="✂️")
                split_button.callback = self.split_callback
                self.add_item(split_button)

    async def hit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return

        # Check if this is a split game
        if interaction.user.id in split_in_progress:
            current = split_hands[interaction.user.id]
            current_hand = current["hand1"] if current["active"] == 1 else current["hand2"]

            # Add card to current split hand
            if self.game.deck:
                current_hand.append(self.game.deck.pop())
            else:
                current_hand.append(draw_card())

            if calculate_score(current_hand) > 21:
                # Hand busted - continue to next hand without showing popup
                if current["active"] == 1:
                    current["active"] = 2
                    split_view = SplitHandButtonView(interaction.user.id)
                    await split_view.show_split_hand_response(interaction, interaction.user.id)
                else:
                    split_view = SplitHandButtonView(interaction.user.id)
                    await split_view.finish_split_game(interaction, interaction.user.id)
            else:
                split_view = SplitHandButtonView(interaction.user.id)
                await split_view.show_split_hand_response(interaction, interaction.user.id)
            return

        await self.handle_hit(interaction, self.game)

    async def stand_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return

        # Check if this is a split game
        if interaction.user.id in split_in_progress:
            current = split_hands[interaction.user.id]
            if current["active"] == 1:
                current["active"] = 2
                split_view = SplitHandButtonView(interaction.user.id)
                await split_view.show_split_hand_response(interaction, interaction.user.id)
            else:
                split_view = SplitHandButtonView(interaction.user.id)
                await split_view.finish_split_game(interaction, interaction.user.id)
            return

        await self.handle_stand(interaction, self.game)

    async def forfeit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return
        await self.handle_forfeit(interaction, self.game)

    async def double_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return
        await self.handle_double_down(interaction, self.game)

    async def split_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return
        await self.handle_split(interaction, self.game)

    async def handle_hit(self, interaction, game):
        result = game.hit()
        player_total = calculate_score(game.player_hand)

        if result == "bust":
            # Player busted
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total,
                show_dealer_total=True
            )
            embed.color = discord.Color.red()
            embed.set_footer(text="💥 BUST! You went over 21!")

            # Update player data
            player_data = load_player_data()
            user_id = str(interaction.user.id)

            if user_id not in player_data:
                player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

            player_data[user_id]["losses"] += 1
            save_player_data(player_data)

            # Update blackjack data
            blackjack_data = load_blackjack_data()
            if user_id not in blackjack_data:
                blackjack_data[user_id] = {"wins": 0, "losses": 0}
            blackjack_data[user_id]["losses"] += 1
            save_blackjack_data(blackjack_data)

            # Save game data before deleting
            game_data = {
                'player_hand': game.player_hand.copy(),
                'dealer_hand': game.dealer_hand.copy()
            }
            del active_games[interaction.user.id]

            # Show end game message
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, game.bet_amount)
        else:
            # Continue game
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total
            )

            view = BlackjackButtonView(game)
            await interaction.response.edit_message(embed=embed, view=view)

    async def handle_stand(self, interaction, game):
        # Dealer plays
        game.dealer_play()
        game.game_over = True

        result = game.get_result()
        player_total = calculate_score(game.player_hand)
        dealer_total = calculate_score(game.dealer_hand)

        embed = create_blackjack_embed(
            interaction.user.display_name,
            game.player_hand,
            game.dealer_hand,
            player_total,
            show_dealer_total=True
        )

        # Update player data
        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        # Update blackjack data
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}

        if result in ["player_wins", "dealer_bust", "blackjack"]:
            embed.color = discord.Color.green()
            if result == "blackjack":
                embed.set_footer(text="🃏 BLACKJACK! You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2.5)  # 1.5x profit + original bet
            elif result == "dealer_bust":
                embed.set_footer(text="💥 Dealer busted! You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2)  # 1x profit + original bet
            else:
                embed.set_footer(text="🎉 You win!")
                player_data[user_id]["chips"] += int(game.bet_amount * 2)  # 1x profit + original bet

            player_data[user_id]["wins"] += 1
            blackjack_data[user_id]["wins"] += 1

        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            embed.color = discord.Color.red()
            if result == "dealer_blackjack":
                embed.set_footer(text="🃏 Dealer has blackjack! You lose!")
            else:
                embed.set_footer(text="😔 You lose!")

            player_data[user_id]["losses"] += 1
            blackjack_data[user_id]["losses"] += 1

        else:  # push
            embed.color = discord.Color.orange()
            embed.set_footer(text="🤝 It's a tie!")
            player_data[user_id]["chips"] += game.bet_amount

        save_player_data(player_data)
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message
        if result in ["player_wins", "dealer_bust", "blackjack"]:
            await end_blackjack_game(interaction, interaction.user, None, "win", game.bet_amount, game_data, game.bet_amount)
        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, game.bet_amount)
        else:  # push
            await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", game.bet_amount, game_data, game.bet_amount)

    async def handle_forfeit(self, interaction, game):
        player_total = calculate_score(game.player_hand)

        # Update player data
        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        player_data[user_id]["losses"] += 1
        save_player_data(player_data)

        # Update blackjack data
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}
        blackjack_data[user_id]["losses"] += 1
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message with rematch button
        await end_blackjack_game(interaction, None, interaction.user, "forfeit", game.bet_amount, game_data, game.bet_amount)

    async def handle_double_down(self, interaction, game):
        player_data = load_player_data()
        user_id = str(interaction.user.id)

        if user_id not in player_data:
            player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

        if player_data[user_id]["chips"] < game.bet_amount:
            await interaction.response.send_message("Not enough chips to double down!", ephemeral=True)
            return

        if not game.can_double_down():
            await interaction.response.send_message("Cannot double down at this time!", ephemeral=True)
            return

        # Deduct additional bet
        player_data[user_id]["chips"] -= game.bet_amount
        save_player_data(player_data)

        # Double down
        game.double_down()

        # Dealer plays
        game.dealer_play()

        result = game.get_result()
        player_total = calculate_score(game.player_hand)

        embed = create_blackjack_embed(
            interaction.user.display_name,
            game.player_hand,
            game.dealer_hand,
            player_total,
            show_dealer_total=True
        )

        # Update results
        player_data = load_player_data()
        blackjack_data = load_blackjack_data()
        if user_id not in blackjack_data:
            blackjack_data[user_id] = {"wins": 0, "losses": 0}

        if result in ["player_wins", "dealer_bust", "blackjack"]:
            embed.color = discord.Color.green()
            embed.set_footer(text="🎉 Double down win!")
            player_data[user_id]["chips"] += int(game.bet_amount * 2)  # This is correct since bet was already doubled
            player_data[user_id]["wins"] += 1
            blackjack_data[user_id]["wins"] += 1

        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            embed.color = discord.Color.red()
            embed.set_footer(text="😔 Double down loss!")
            player_data[user_id]["losses"] += 1
            blackjack_data[user_id]["losses"] += 1

        else:  # push
            embed.color = discord.Color.orange()
            embed.set_footer(text="🤝 Double down tie!")
            player_data[user_id]["chips"] += game.bet_amount

        save_player_data(player_data)
        save_blackjack_data(blackjack_data)

        # Save game data before deleting
        game_data = {
            'player_hand': game.player_hand.copy(),
            'dealer_hand': game.dealer_hand.copy()
        }
        del active_games[interaction.user.id]

        # Show end game message
        original_bet = game.bet_amount // 2  # Get original bet before doubling
        if result in ["player_wins", "dealer_bust", "blackjack"]:
            await end_blackjack_game(interaction, interaction.user, None, "win", game.bet_amount, game_data, original_bet)
        elif result in ["dealer_wins", "player_bust", "dealer_blackjack"]:
            await end_blackjack_game(interaction, None, interaction.user, "lose", game.bet_amount, game_data, original_bet)
        else:  # push
            await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", game.bet_amount, game_data, original_bet)

    async def handle_split(self, interaction, game):
        user_id = interaction.user.id

        # Check if player can afford to split (need to match current bet)
        player_data = load_player_data()
        user_id_str = str(user_id)

        if user_id_str not in player_data:
            player_data[user_id_str] = {"chips": 500, "wins": 0, "losses": 0}

        if player_data[user_id_str]["chips"] < game.bet_amount:
            await interaction.response.send_message("Not enough chips to split! You need to match your original bet.", ephemeral=True)
            return

        # Deduct split bet
        player_data[user_id_str]["chips"] -= game.bet_amount
        save_player_data(player_data)

        # Create split hands
        player_hand = game.player_hand
        new_card1 = game.deck.pop() if game.deck else draw_card()
        new_card2 = game.deck.pop() if game.deck else draw_card()

        split_hands[user_id] = {
            "hand1": [player_hand[0], new_card1],  # First card + new card
            "hand2": [player_hand[1], new_card2],  # Second card + new card
            "active": 1,  # Start with hand 1
            "bet_amount": game.bet_amount
        }
        split_in_progress.add(user_id)

        await self.show_split_hand(interaction, user_id)

    async def show_split_hand(self, interaction, user_id):
        split_data = split_hands[user_id]
        active_hand = split_data["active"]

        # Create embed for split hands
        embed = discord.Embed(
            title=f"🃏 {interaction.user.display_name}'s Split Hands 🃏",
            color=discord.Color.blue()
        )

        # Hand 1
        hand1_cards = ''.join(split_data["hand1"])
        hand1_score = calculate_score(split_data["hand1"])
        hand1_indicator = "👈 **ACTIVE**" if active_hand == 1 else ""
        embed.add_field(
            name=f"✋ Hand 1 {hand1_indicator}", 
            value=f"{hand1_cards} ({hand1_score})", 
            inline=False
        )

        # Hand 2
        hand2_cards = ''.join(split_data["hand2"])
        hand2_score = calculate_score(split_data["hand2"])
        hand2_indicator = "👈 **ACTIVE**" if active_hand == 2 else ""
        embed.add_field(
            name=f"✋ Hand 2 {hand2_indicator}", 
            value=f"{hand2_cards} ({hand2_score})", 
            inline=False
        )

        # Dealer hand (keep hidden)
        game = active_games.get(user_id)
        if game:
            dealer_cards = f"{game.dealer_hand[0]} ❓"
            visible_card_value = calculate_score([game.dealer_hand[0]])
            dealer_value = f"({visible_card_value} + ?)"
            embed.add_field(name="🏛️ Dealer Hand", value=f"{dealer_cards} {dealer_value}", inline=False)

        # Create buttons for split hand actions
        view = SplitHandButtonView(user_id)
        await interaction.response.edit_message(embed=embed, view=view)

class SplitHandButtonView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)  # Increase timeout to 2 minutes
        self.user_id = user_id

        # Create buttons for split hand actions
        hit_button = Button(label="Hit", style=discord.ButtonStyle.primary, custom_id="hit", emoji="🟦")
        hit_button.callback = self.hit_callback

        stand_button = Button(label="Stand", style=discord.ButtonStyle.secondary, custom_id="stand", emoji="✋")
        stand_button.callback = self.stand_callback

        self.add_item(hit_button)
        self.add_item(stand_button)

    async def hit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return
        await self.handle_split_action(interaction, "hit")

    async def stand_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return
        await self.handle_split_action(interaction, "stand")

    async def handle_split_action(self, interaction, action):
        user_id = interaction.user.id

        if user_id not in split_in_progress:
            await interaction.response.send_message("No active split game found!", ephemeral=True)
            return

        current = split_hands[user_id]
        current_hand = current["hand1"] if current["active"] == 1 else current["hand2"]

        if action == "hit":
            # Get the deck from the active game
            game = active_games.get(user_id)
            if game and game.deck:
                current_hand.append(game.deck.pop())
            else:
                # Fallback: create a new card
                current_hand.append(draw_card())

            # Check if hand busted - no popup, just continue to next hand or finish
            if calculate_score(current_hand) > 21:
                if current["active"] == 1:
                    current["active"] = 2
                    await self.show_split_hand_response(interaction, user_id)
                else:
                    await self.finish_split_game(interaction, user_id)
            else:
                await self.show_split_hand_response(interaction, user_id)

        elif action == "stand":
            if current["active"] == 1:
                current["active"] = 2
                await self.show_split_hand_response(interaction, user_id)
            else:
                await self.finish_split_game(interaction, user_id)

    async def show_split_hand_response(self, interaction, user_id):
        split_data = split_hands[user_id]
        active_hand = split_data["active"]

        # Create embed for split hands
        embed = discord.Embed(
            title=f"🃏 {interaction.user.display_name}'s Split Hands 🃏",
            color=discord.Color.blue()
        )

        # Hand 1
        hand1_cards = ''.join(split_data["hand1"])
        hand1_score = calculate_score(split_data["hand1"])
        hand1_indicator = "👈 **ACTIVE**" if active_hand == 1 else ""
        hand1_status = " (BUST)" if hand1_score > 21 else ""
        embed.add_field(
            name=f"✋ Hand 1 {hand1_indicator}", 
            value=f"{hand1_cards} ({hand1_score}){hand1_status}", 
            inline=False
        )

        # Hand 2
        hand2_cards = ''.join(split_data["hand2"])
        hand2_score = calculate_score(split_data["hand2"])
        hand2_indicator = "👈 **ACTIVE**" if active_hand == 2 else ""
        hand2_status = " (BUST)" if hand2_score > 21 else ""
        embed.add_field(
            name=f"✋ Hand 2 {hand2_indicator}", 
            value=f"{hand2_cards} ({hand2_score}){hand2_status}", 
            inline=False
        )

        # Dealer hand (keep hidden)
        game = active_games.get(user_id)
        if game:
            dealer_cards = f"{game.dealer_hand[0]} ❓"
            visible_card_value = calculate_score([game.dealer_hand[0]])
            dealer_value = f"({visible_card_value} + ?)"
            embed.add_field(name="🏛️ Dealer Hand", value=f"{dealer_cards} {dealer_value}", inline=False)

        # Create buttons for split hand actions
        view = SplitHandButtonView(user_id)
        
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            # Fallback method
            try:
                await interaction.followup.edit_message(interaction.message.id, embed=embed, view=view)
            except:
                pass

    async def finish_split_game(self, interaction, user_id):
        game = active_games.get(user_id)
        if not game:
            await interaction.response.send_message("No active game found!", ephemeral=True)
            return

        # Dealer plays
        game.dealer_play()

        split_data = split_hands[user_id]
        hand1 = split_data["hand1"]
        hand2 = split_data["hand2"]
        bet_amount = split_data["bet_amount"]

        hand1_score = calculate_score(hand1)
        hand2_score = calculate_score(hand2)
        dealer_score = calculate_score(game.dealer_hand)

        # Calculate results for each hand
        hand1_result = self.get_hand_result(hand1_score, dealer_score, len(hand1))
        hand2_result = self.get_hand_result(hand2_score, dealer_score, len(hand2))

        # Create final results embed
        embed = discord.Embed(
            title=f"🃏 {interaction.user.display_name}'s Split Results 🃏",
            color=discord.Color.blue()
        )

        # Hand 1 result
        hand1_color = "🟢" if hand1_result in ["win", "blackjack"] else "🔴" if hand1_result == "lose" else "🟡"
        embed.add_field(
            name=f"✋ Hand 1 {hand1_color}",
            value=f"{''.join(hand1)} ({hand1_score})\n**{hand1_result.upper()}**",
            inline=False
        )

        # Hand 2 result
        hand2_color = "🟢" if hand2_result in ["win", "blackjack"] else "🔴" if hand2_result == "lose" else "🟡"
        embed.add_field(
            name=f"✋ Hand 2 {hand2_color}",
            value=f"{''.join(hand2)} ({hand2_score})\n**{hand2_result.upper()}**",
            inline=False
        )

        # Dealer hand
        embed.add_field(
            name="🏛️ Dealer Hand",
            value=f"{''.join(game.dealer_hand)} ({dealer_score})",
            inline=False
        )

        # Calculate chip changes
        chip_change = 0
        if hand1_result == "win":
            chip_change += bet_amount * 2
        elif hand1_result == "blackjack":
            chip_change += int(bet_amount * 2.5)
        elif hand1_result == "tie":
            chip_change += bet_amount

        if hand2_result == "win":
            chip_change += bet_amount * 2
        elif hand2_result == "blackjack":
            chip_change += int(bet_amount * 2.5)
        elif hand2_result == "tie":
            chip_change += bet_amount

        net_change = chip_change - (bet_amount * 2)  # Subtract both original bets

        # Update player data
        player_data = load_player_data()
        user_id_str = str(user_id)
        player_data[user_id_str]["chips"] += chip_change

        # Update win/loss stats
        wins = 0
        losses = 0
        if hand1_result in ["win", "blackjack"]:
            wins += 1
        elif hand1_result == "lose":
            losses += 1

        if hand2_result in ["win", "blackjack"]:
            wins += 1
        elif hand2_result == "lose":
            losses += 1

        player_data[user_id_str]["wins"] += wins
        player_data[user_id_str]["losses"] += losses
        save_player_data(player_data)

        # Update blackjack data
        blackjack_data = load_blackjack_data()
        if user_id_str not in blackjack_data:
            blackjack_data[user_id_str] = {"wins": 0, "losses": 0}
        blackjack_data[user_id_str]["wins"] += wins
        blackjack_data[user_id_str]["losses"] += losses
        save_blackjack_data(blackjack_data)

        # Add summary
        chip_text = f"+{net_change}" if net_change > 0 else str(net_change)
        embed.add_field(
            name="💰 Final Result",
            value=f"**{chip_text} chips**\nWins: {wins} | Losses: {losses}",
            inline=False
        )

        # Clean up split game data
        del split_hands[user_id]
        split_in_progress.discard(user_id)
        del active_games[user_id]

        # Add rematch button
        view = RematchView(bet_amount, user_id)

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            # Fallback: try to send a new message if editing fails
            try:
                await interaction.followup.send(embed=embed, view=view)
            except:
                pass

    def get_hand_result(self, hand_score, dealer_score, hand_length):
        if hand_score > 21:
            return "lose"  # Busted
        elif dealer_score > 21:
            return "win"   # Dealer busted
        elif hand_score == 21 and hand_length == 2:
            if dealer_score == 21:
                return "tie"
            return "blackjack"
        elif hand_score > dealer_score:
            return "win"
        elif dealer_score > hand_score:
            return "lose"
        else:
            return "tie"

# Rematch button
class RematchView(discord.ui.View):
    def __init__(self, bet_amount, original_user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bet_amount = bet_amount
        self.original_user_id = original_user_id

    @discord.ui.button(label="Rematch", style=discord.ButtonStyle.success, emoji="🔄")
    async def rematch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("This isn't your game! Start your own with `$blackjack`", ephemeral=True)
            return

        # Check if interaction is still valid
        try:
            if interaction.response.is_done():
                return
        except:
            return

        user_id = str(interaction.user.id)

        # Load player data
        player_data = load_player_data()

        # Check if player has enough chips
        if player_data[user_id]["chips"] < self.bet_amount:
            await interaction.response.send_message(f"You don't have enough chips! You have {player_data[user_id]['chips']} chips.", ephemeral=True)
            return

        # Deduct bet from player chips
        player_data[user_id]["chips"] -= self.bet_amount
        save_player_data(player_data)

        # Create new game
        game = BlackjackGame(interaction.user.id, self.bet_amount)
        active_games[interaction.user.id] = game

        player_total = calculate_score(game.player_hand)

        # Check for immediate blackjack
        if player_total == 21:
            dealer_total = calculate_score(game.dealer_hand)
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total,
                show_dealer_total=True
            )

            # Update blackjack data first
            blackjack_data = load_blackjack_data()
            if user_id not in blackjack_data:
                blackjack_data[user_id] = {"wins": 0, "losses": 0}

            if dealer_total == 21:
                embed.color = discord.Color.orange()
                embed.set_footer(text="🤝 Both have blackjack! It's a tie!")
                player_data[user_id]["chips"] += self.bet_amount  # Refund bet - no win/loss recorded
            else:
                embed.color = discord.Color.green()
                embed.set_footer(text="🃏 BLACKJACK! You win!")
                player_data[user_id]["chips"] += int(self.bet_amount * 2.5)  # 1.5x profit + original bet
                player_data[user_id]["wins"] += 1
                blackjack_data[user_id]["wins"] += 1

            save_blackjack_data(blackjack_data)
            save_player_data(player_data)
            del active_games[interaction.user.id]

            # Show end game message with rematch button
            game_data = {
                'player_hand': game.player_hand.copy(),
                'dealer_hand': game.dealer_hand.copy()
            }
            if dealer_total == 21:
                await end_blackjack_game(interaction, interaction.user, interaction.user, "tie", self.bet_amount, game_data, self.bet_amount)
            else:
                await end_blackjack_game(interaction, interaction.user, None, "win", self.bet_amount, game_data, self.bet_amount)
        else:
            # Normal game start
            embed = create_blackjack_embed(
                interaction.user.display_name,
                game.player_hand,
                game.dealer_hand,
                player_total
            )

            view = BlackjackButtonView(game)
            await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True

# Commands
@bot.command()
async def blackjack(ctx):
    user_id = str(ctx.author.id)

    # Check if user already has an active game and clear it
    if ctx.author.id in active_games:
        del active_games[ctx.author.id]
        await ctx.send("🔄 Cleared your previous game and starting a new one!")

    # Load player data
    player_data = load_player_data()

    if user_id not in player_data:
        player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}
        save_player_data(player_data)

    user_chips = player_data[user_id]["chips"]

    # Check if player has enough chips for minimum bet
    if user_chips < 25:
        await ctx.send(f"You need at least 25 chips to play! You have {user_chips} chips. Use `$daily` to get more chips.")
        return

    # Show bet selection menu
    embed = discord.Embed(
        title="🎰 Place Your Bet",
        description=f"💰 You have **{user_chips}** chips\n\nChoose your bet amount:",
        color=discord.Color.blue()
    )

    view = BetSelectionView(user_chips)
    await ctx.send(embed=embed, view=view)

@bot.command(name='bjhelp')
async def bjhelp(ctx):
    embed = discord.Embed(
        title="🃏 Blackjack Bot Help",
        description="Welcome to the Blackjack Bot! Here's everything you need to know:",
        color=0x5865F2
    )

    embed.add_field(
        name="🎯 How to Play",
        value="• Get as close to 21 as possible without going over\n• Face cards (J, Q, K) are worth 10 points\n• Aces are worth 11 or 1 (automatically adjusted)\n• Beat the dealer's hand to win!",
        inline=False
    )

    embed.add_field(
        name="🎮 Game Controls",
        value="• **Hit** - Draw another card\n• **Stand** - Keep your current hand\n• **Forfeit** - Give up and lose the game\n• **Double Down** - Double your bet for one more card",
        inline=False
    )

    embed.add_field(
        name="📋 Commands",
        value="• `$blackjack` - Start a new blackjack game with bet selection\n• `$bjstats` - View your personal statistics\n• `$bjstats @user` - View another player's statistics\n• `$chips` - Check your current chip balance\n• `$daily` - Claim your daily 200 chip bonus\n• `$bjleaderboard` - View top 10 players by wins\n• `$bjhelp` - Show this help message",
        inline=False
    )

    embed.add_field(
        name="💰 Betting System",
        value="• Choose from 25, 50, or 100 chip bets\n• Blackjack pays 2.5x your bet\n• Regular wins pay 2x your bet\n• Ties return your bet",
        inline=False
    )

    embed.add_field(
        name="🏆 Winning Conditions",
        value="• **Blackjack**: Get 21 with your first two cards (2.5x payout)\n• **Beat Dealer**: Get closer to 21 than the dealer\n• **Dealer Busts**: Dealer goes over 21\n• **Bust**: Going over 21 = automatic loss",
        inline=False
    )

    embed.set_footer(text="Good luck at the tables! 🍀")

    await ctx.send(embed=embed)

@bot.command()
async def chips(ctx):
    user_id = str(ctx.author.id)
    player_data = load_player_data()

    if user_id not in player_data:
        player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}
        save_player_data(player_data)

    chips = player_data[user_id]["chips"]
    await ctx.send(f"💰 {ctx.author.display_name} has **{chips}** chips!")

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    player_data = load_player_data()

    if user_id not in player_data:
        player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0, "last_daily": None}

    # Check if user has claimed daily today
    today = datetime.date.today().isoformat()
    last_daily = player_data[user_id].get("last_daily")

    if last_daily and last_daily.startswith(today):
        await ctx.send("You've already claimed your daily chips today! Come back tomorrow.")
        return

    # Give daily chips
    player_data[user_id]["chips"] += 200
    player_data[user_id]["last_daily"] = datetime.datetime.now().isoformat()
    save_player_data(player_data)

    await ctx.send(f"💰 {ctx.author.display_name} claimed 200 daily chips! You now have **{player_data[user_id]['chips']}** chips!")

@bot.command()
async def bjstats(ctx, user: discord.Member = None):
    if user is None:
        user = ctx.author

    user_id = str(user.id)
    blackjack_data = load_blackjack_data()
    player_data = load_player_data()

    if user_id not in blackjack_data:
        await ctx.send(f"{user.display_name} hasn't played any blackjack games yet!")
        return

    wins = blackjack_data[user_id]["wins"]
    losses = blackjack_data[user_id]["losses"]
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0

    # Get chips from player data
    chips = player_data.get(user_id, {}).get("chips", 0)

    embed = discord.Embed(
        title=f"🃏 {user.display_name}'s Blackjack Stats",
        color=discord.Color.blue()
    )

    # Display user's profile picture
    embed.set_thumbnail(url=user.avatar.url)

    embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
    embed.add_field(name="💔 Losses", value=str(losses), inline=True)
    embed.add_field(name="🎮 Total Games", value=str(total_games), inline=True)
    embed.add_field(name="📊 Win Rate", value=f"{win_rate:.1f}%", inline=True)
    embed.add_field(name="💰 Chips", value=str(chips), inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def bjadmin(ctx, user: discord.Member = None):
    # If no user is mentioned, give chips to the command author
    target_user = user if user else ctx.author
    user_id = str(target_user.id)
    player_data = load_player_data()

    if user_id not in player_data:
        player_data[user_id] = {"chips": 500, "wins": 0, "losses": 0}

    # Add 500 chips
    player_data[user_id]["chips"] += 500
    save_player_data(player_data)

    if user:
        await ctx.send(f"🔧 Admin: Added 500 chips to {target_user.display_name}! They now have **{player_data[user_id]['chips']}** chips!")
    else:
        await ctx.send(f"🔧 Admin: Added 500 chips to {ctx.author.display_name}! You now have **{player_data[user_id]['chips']}** chips!")

@bot.command()
async def bjleaderboard(ctx):
    blackjack_data = load_blackjack_data()

    if not blackjack_data:
        await ctx.send("No blackjack games have been played yet!")
        return

    # Sort by wins
    leaderboard = []
    for user_id, stats in blackjack_data.items():
        wins = stats["wins"]
        losses = stats["losses"]

        try:
            user = await bot.fetch_user(int(user_id))
            username = user.name if user else f"Unknown User"
        except:
            try:
                # Fallback to get_user if fetch_user fails
                user = bot.get_user(int(user_id))
                username = user.name if user else f"Unknown User"
            except:
                username = f"Unknown User"

        leaderboard.append((username, wins, losses))

    # Sort by wins (descending)
    leaderboard.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Blackjack Leaderboard",
        description="Top 10 players by wins:",
        color=0xFFD700
    )

    leaderboard_text = ""
    for i, (username, wins, losses) in enumerate(leaderboard[:10]):
        rank = f"#{i+1}"
        leaderboard_text += f"**{rank} {username}** - W: {wins} | L: {losses}\n"

    embed.add_field(name="", value=leaderboard_text, inline=False)

    await ctx.send(embed=embed)

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# Sassy message lists - 60 total lines!
bot_win_lines = [
    "Better luck next time, sweetie. The house always wins 💅",
    "That hand? Trash. But thanks for the donation.",
    "Did you even *try*?",
    "You fold like my grandma's laundry.",
    "Call 911 — you just got robbed.",
    "You lost to a bot. A **bot**. Embarrassing.",
    "You played yourself.",
    "I didn't even break a sweat.",
    "Scoreboard says you owe me sympathy.",
    "Tough game? No, *you're* just bad.",
    "Next time bring something better than your luck… oh wait.",
    "Ouch… that had to hurt.",
    "I'd say it was close, but I'd be lying.",
    "Please don't cry. I only deal cards.",
    "Is that your best? Bless your heart.",
    "You nearly had me… at like 5% effort.",
    "Cue the sad violin.",
    "Thanks for playing my charity round.",
    "Do you need tissues or extra consolation?",
    "Check under your seat — that's where your dignity is."
]

player_win_lines = [
    "Wait—no! That's cheating. Run it back!",
    "Ugh. I'm calling my supervisor.",
    "Fine. Take your little win.",
    "Beginner's luck. Don't get cocky.",
    "Okay… who unplugged my RNG?",
    "Whatever. I totally let you win.",
    "This will not be forgotten.",
    "You must be feeling real proud.",
    "Destroying code feels… weird.",
    "I guess even bots get burned sometimes.",
    "Happy? Go buy yourself a trophy.",
    "One round in your favor — I'll remember this.",
    "Well aren't you the prodigy?",
    "Not fair! You had skill.",
    "I'll get you next time… I swear.",
    "Congrats, you beat a dealer with no feelings.",
    "Take a victory lap, champ.",
    "My circuits need a minute after that one.",
    "Be proud: you outplayed artificial intelligence.",
    "That's what you get for underestimating me."
]

tie_lines = [
    "A tie? Lame. I wanted carnage.",
    "Well this was anti‑climactic.",
    "I didn't lose — and that's what matters.",
    "You got lucky I didn't finish the job.",
    "Next round, *you're* going down.",
    "Hold my cards — I'm not impressed.",
    "Equal? Hardly satisfying.",
    "It's a tie… which is just sad.",
    "Let's call it a truce… for now.",
    "Someone's stalling. Next.",
    "Awkward. We both tried kinda hard.",
    "Well, that went nowhere.",
    "Half a win is still half.",
    "Stalemate. How boring.",
    "A draw… yawns the dealer.",
    "Nobody wins here. Move along.",
    "Equal parts wasted effort.",
    "Meh. Let's not do that again.",
    "States like this irritate me.",
    "Tie game. Groan-worthy."
]

from discord import Embed, ButtonStyle
from discord.ui import View, Button

async def end_blackjack_game(interaction, winner, loser, result, bet_amount, game_data, original_bet):
    # Create the main game embed showing final hands
    embed = create_blackjack_embed(
        interaction.user.display_name,
        game_data['player_hand'],
        game_data['dealer_hand'],
        calculate_score(game_data['player_hand']),
        show_dealer_total=True
    )

    # Calculate chip changes and set color/status based on result
    if result == "win":
        embed.color = discord.Color.green()
        status_emoji = "🎉"
        status_text = f"{winner.mention} wins!"
        # Check if it's a blackjack (21 with 2 cards) or if the result was specifically "blackjack"
        player_score = calculate_score(game_data['player_hand'])
        is_blackjack = (player_score == 21 and len(game_data['player_hand']) == 2)

        if is_blackjack:
            chip_gain = int(bet_amount * 1.5)  # Blackjack pays 1.5x profit
            chip_text = f"💰 **+{chip_gain} chips** (Blackjack bonus!)"
        else:
            chip_gain = bet_amount  # Regular win pays 1x profit
            chip_text = f"💰 **+{chip_gain} chips**"
    elif result in ["lose", "forfeit"]:
        embed.color = discord.Color.red()
        status_emoji = "💔" if result == "lose" else "🏳️"
        status_text = f"{loser.mention} {'loses!' if result == 'lose' else 'forfeited!'}"
        chip_text = f"💸 **-{bet_amount} chips**"
    else:  # tie
        embed.color = discord.Color.orange()
        status_emoji = "🤝"
        status_text = "It's a tie!"
        chip_text = f"💰 **±0 chips** (Bet returned)"

    # Get sassy line based on result
    if result == "win":
        sassy_line = random.choice(player_win_lines)
    elif result in ["lose", "forfeit"]:
        sassy_line = random.choice(bot_win_lines)
    else:  # tie
        sassy_line = random.choice(tie_lines)

    # Add game over field with sassy message and chip info
    embed.add_field(
        name=f"{status_emoji} Game Over!",
        value=f"**{status_text}**\n{chip_text}\n\n*{sassy_line}*",
        inline=False
    )

    # Create rematch view with proper user validation and timeout handling
    view = RematchView(original_bet, interaction.user.id)

    try:
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=view)
    except discord.errors.InteractionResponded:
        await interaction.edit_original_response(embed=embed, view=view)
    except Exception as e:
        # Fallback: try to send a new message if editing fails
        try:
            await interaction.followup.send(embed=embed, view=view)
        except:
            pass


# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
