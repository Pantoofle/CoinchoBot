from carte import Color
from utils import delete_message


class Player():
    def __init__(self, user, index, table):
        self.user = user
        self.hand = []
        self.hand_msg = None
        self.cards_won = []
        self.team = index % 2
        self.index = index
        self.mention = user.mention
        self.next = None
        self.table = table

    async def update_hand(self):
        if self.hand == []:
            return

        txt = "[table {}] Ta main :".format(self.table)
        for color in Color:
            txt += "\n {} : ".format(color)
            txt += "".join([str(card.value) for card in
                            self.hand if card.color == color])

        if self.hand_msg is not None:
            await self.hand_msg.edit(content=txt)
        else:
            self.hand_msg = await self.user.send(txt)

    def sort_hand(self, trumps=[]):
        self.hand.sort(
            key=lambda c: c.strength(trumps, None),
            reverse=True)

    async def receive_hand(self, hand):
        self.hand = hand
        self.sort_hand()
        await self.update_hand()

    async def play_card(self, card):
        self.hand.remove(card)
        await self.update_hand()

    def count_points(self, trumps):
        points = sum([c.points(trumps) for c in self.cards_won])
        tricks = len(self.cards_won) // 4
        return(points, tricks)

    async def clean_hand(self):
        self.hand = []
        await delete_message(self.hand_msg)
        self.hand_msg = None

    async def change_owner(self, user):
        self.user = user
        self.mention = user.mention

        await delete_message(self.hand_msg)
        self.hand_msg = None
        await self.update_hand()
