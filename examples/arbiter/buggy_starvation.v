// Buggy submission (corpus running example, §4.2): the priority pointer fails to
// rotate past the served line — `base <= gidx` instead of `base <= gidx + 1`.
// It keeps the just-served requester at highest priority, so under held requests
// (e.g. req = 0101) a lower line starves. Compiles (L0 ok), satisfies P1 and P2,
// but L1 emits REJ with a fairness/starvation diagnosis.
module arbiter_rr (
    input            clk,
    input            rst_n,
    input      [3:0] req,
    output reg [3:0] grant
);
    reg [1:0] base;
    integer   i;
    reg [1:0] cand;
    reg [1:0] gidx;
    reg       found;

    always @(*) begin
        grant = 4'b0000;
        found = 1'b0;
        gidx  = base;
        for (i = 0; i < 4; i = i + 1) begin
            cand = base + i[1:0];
            if (!found && req[cand]) begin
                grant = 4'b0001 << cand;
                gidx  = cand;
                found = 1'b1;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            base <= 2'd0;
        else if (found)
            base <= gidx;                // BUG: no +1 -> served line keeps priority
    end
endmodule
