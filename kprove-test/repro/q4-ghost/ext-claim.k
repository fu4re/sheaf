requires "ext-addcell.k"
module EXT-CLAIM
  imports EXT-ADDCELL
  // The ghost cell <callCounter> is constrained in BOTH Pre and Post:
  // start at C, one step of `5` increments acct by 5; assert callCounter unchanged
  // and non-negative -> shows the ghost cell is visible/constrainable in claims.
  claim <k> 5 => 6 </k>
        <acct> A => A +Int 5 </acct>
        <callCounter> C => C </callCounter>
    requires C >=Int 0
    [label(ghost-constrainable)]
endmodule
