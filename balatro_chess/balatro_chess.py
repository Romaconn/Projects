import argparse
import random
import chess


class Card:
    """Base card providing special effects during the game."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def apply(self, game, color: chess.Color) -> None:
        raise NotImplementedError


class ExtraMoveCard(Card):
    def __init__(self):
        super().__init__("Extra Move", "Take an additional move immediately")

    def apply(self, game, color: chess.Color) -> None:
        game.extra_turn = True


class KnightShiftCard(Card):
    def __init__(self):
        super().__init__(
            "Knight Shift", "Move any one of your pieces as a knight for this move"
        )

    def apply(self, game, color: chess.Color) -> None:
        game.knight_override = True


def build_deck():
    deck = [ExtraMoveCard(), ExtraMoveCard(), KnightShiftCard(), KnightShiftCard()]
    random.shuffle(deck)
    return deck


class BalatroChess:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.decks = {chess.WHITE: build_deck(), chess.BLACK: build_deck()}
        self.hands = {chess.WHITE: [], chess.BLACK: []}
        self.extra_turn = False
        self.knight_override = False

    def draw_card(self, color: chess.Color) -> None:
        deck = self.decks[color]
        if deck:
            card = deck.pop()
            self.hands[color].append(card)
            print(f"Drawn card: {card.name} - {card.description}")

    def play(self) -> None:
        current = chess.WHITE
        while not self.board.is_game_over():
            print("\n" + str(self.board))
            self.draw_card(current)
            hand = self.hands[current]
            if hand:
                print("Hand:")
                for idx, card in enumerate(hand):
                    print(f"  {idx}: {card.name} - {card.description}")
                choice = input("Play a card? (index or blank) ")
                if choice:
                    try:
                        card = hand.pop(int(choice))
                    except (ValueError, IndexError):
                        print("Invalid choice")
                        continue
                    card.apply(self, current)
            move = self._get_move(current)
            if move is None:
                continue
            self.board.push(move)
            if self.extra_turn:
                print("Extra move granted!")
                self.extra_turn = False
                continue
            current = not current
        print("Game over:", self.board.result())

    def _get_move(self, color: chess.Color) -> chess.Move | None:
        if self.knight_override:
            raw = input("Knight override move (e.g., e2e3): ")
            move = self._knight_move_from_uci(raw, color)
            if move:
                self.knight_override = False
            return move
        raw = input("Enter move in UCI (e.g., e2e4): ")
        try:
            move = chess.Move.from_uci(raw)
        except ValueError:
            print("Bad move format")
            return None
        if move not in self.board.legal_moves:
            print("Illegal move")
            return None
        return move

    def _knight_move_from_uci(self, uci: str, color: chess.Color) -> chess.Move | None:
        try:
            from_sq = chess.parse_square(uci[:2])
            to_sq = chess.parse_square(uci[2:4])
        except ValueError:
            print("Bad move format")
            return None
        piece = self.board.piece_at(from_sq)
        if not piece or piece.color != color:
            print("No piece at source")
            return None
        file_diff = abs(chess.square_file(from_sq) - chess.square_file(to_sq))
        rank_diff = abs(chess.square_rank(from_sq) - chess.square_rank(to_sq))
        if not ((file_diff == 1 and rank_diff == 2) or (file_diff == 2 and rank_diff == 1)):
            print("Not a knight move")
            return None
        target_piece = self.board.piece_at(to_sq)
        if target_piece and target_piece.color == color:
            print("Cannot capture own piece")
            return None
        move = chess.Move(from_sq, to_sq, promotion=None)
        return move

    def demo(self) -> None:
        print("Demo starting...")
        print(self.board)
        self.draw_card(chess.WHITE)
        self.draw_card(chess.BLACK)
        print(
            "White hand:", [card.name for card in self.hands[chess.WHITE]],
            "\nBlack hand:", [card.name for card in self.hands[chess.BLACK]],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chess with Balatro-style cards")
    parser.add_argument("--demo", action="store_true", help="run a quick demonstration")
    args = parser.parse_args()
    game = BalatroChess()
    if args.demo:
        game.demo()
    else:
        game.play()


if __name__ == "__main__":
    main()
