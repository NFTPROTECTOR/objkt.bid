import smartpy as sp

class OBJKTBID(sp.Contract):
    def __init__(self, objkt, management_fee, hicetnunc_fee, admin, hicetnunc):
        self.add_flag('initial-cast')
        self.add_flag("protocol", "florence")
        self.fee = 0
        self.amount = 0
        self.init(
            swaps = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, xtz_per_objkt=sp.TMutez, objkt_id=sp.TNat)),
            swap_id = 0,
            objkt = objkt,
            management_fee=management_fee,
            hicetnunc_fee=hicetnunc_fee,
            admin = admin,
            hicetnunc= hicetnunc,
            metadata=sp.big_map({"": sp.utils.bytes_of_string("tezos-storage:meta")})
            )

    @sp.entry_point
    def update_admin(self, params):
        sp.verify(sp.sender == self.data.admin)
        self.data.admin = params

    @sp.entry_point
    def update_hicetnunc(self, params):
        sp.verify(sp.sender == self.data.admin)
        self.data.hicetnunc = params

    @sp.entry_point
    def update_hicetnunc_fee(self, params):
        sp.verify(sp.sender == self.data.admin)
        self.data.hicetnunc_fee=params.fee

    @sp.entry_point
    def update_management_fee(self, params):
        sp.verify(sp.sender == self.data.admin)
        self.data.management_fee=params.fee

    @sp.entry_point
    def bid(self, params):
        sp.verify(sp.amount > sp.mutez(0), 'no value in bid')
        self.data.swaps[self.data.swap_id] = sp.record(issuer=sp.sender, objkt_id=params.objkt_id, xtz_per_objkt=sp.amount)
        self.data.swap_id += 1

    @sp.entry_point
    def retract_bid(self, params):
        sp.verify(self.data.swaps[params].issuer == sp.sender)
        sp.send(sp.sender, self.data.swaps[params].xtz_per_objkt)
        del self.data.swaps[params]

    @sp.entry_point
    def swap(self, params):
        sp.verify(sp.sender != self.data.swaps[params.swap_id].issuer)

        # try to send token
        # will fail if owner doesn't have the token
        self.fa2_transfer(self.data.objkt, sp.sender, self.data.swaps[params.swap_id].issuer, self.data.swaps[params.swap_id].objkt_id, 1)

        self.amount =  sp.fst(sp.ediv(self.data.swaps[params.swap_id].xtz_per_objkt, sp.mutez(1)).open_some())

        self.hicetnunc_fee = sp.fst(sp.ediv(sp.utils.nat_to_mutez(self.amount), sp.utils.nat_to_mutez(1)).open_some()) * (self.data.hicetnunc_fee) / 1000
        self.management_fee = sp.fst(sp.ediv(sp.utils.nat_to_mutez(self.amount), sp.utils.nat_to_mutez(1)).open_some()) * (self.data.management_fee) / 1000

        # send management fees
        sp.send(self.data.admin, sp.utils.nat_to_mutez(self.management_fee))

        # send hicetnunc fees
        sp.send(self.data.hicetnunc, sp.utils.nat_to_mutez(self.hicetnunc_fee))

        # send value to objkt seller
        sp.send(sp.sender, self.data.swaps[params.swap_id].xtz_per_objkt - sp.utils.nat_to_mutez(self.management_fee + self.hicetnunc_fee))

        # delete the bid from the map
        del self.data.swaps[params.swap_id]


    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=from_, txs=sp.list([sp.record(amount=objkt_amount, to_=to_, token_id=objkt_id)]))]), sp.mutez(0), c)

