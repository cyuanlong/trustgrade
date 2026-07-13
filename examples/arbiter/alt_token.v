// Valid alternative (§4.2): a rotating-token arbiter, structurally unlike the
// rotating-pointer reference. A token advances one line every cycle and a line
// is granted only while it holds the token and is requesting. This satisfies all
// three properties — mutex (one grant), no-empty-grant (grant only on request),
// and fairness (the token visits every line within N cycles < FAIR_BOUND) — so
// L1 passes and, with no differential harness on this objective, the backbone
// returns ACC. It demonstrates P4: a legitimate alternative is accepted despite
// differing from the reference in both structure and exact grant timing.
module arbiter_rr (
    input            clk,
    input            rst_n,
    input      [3:0] req,
    output reg [3:0] grant
);
    reg [1:0] token;            // which line currently holds the token

    always @(*) begin
        grant = 4'b0000;
        if (req[token])
            grant = 4'b0001 << token;   // serve the token holder iff it requests
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            token <= 2'd0;
        else
            token <= token + 2'd1;      // advance every cycle -> visits all in N
    end
endmodule
