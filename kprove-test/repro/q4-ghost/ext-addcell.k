// Q4 variant 1: can an importing module ADD a ghost cell via its own
// configuration declaration, WITHOUT redeclaring BASE's cells?
requires "base.k"
module EXT-ADDCELL
  imports BASE
  configuration <callCounter> 0 </callCounter>
endmodule
