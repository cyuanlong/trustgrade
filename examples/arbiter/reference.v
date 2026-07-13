// Reference: 4-way round-robin arbiter (rotating priority pointer).
// Contract Phi (see property_tb.v): P1 mutex, P2 no-empty-grant, P3 fairness.
// After serving line g, the base priority rotates to g+1 so every held request
// is granted within N+2 cycles.
module arbiter_rr (
    input            clk,
    input            rst_n,
    input      [3:0] req,
    output reg [3:0] grant
);
    reg [1:0] base;              // lowest-priority-first rotating pointer

    integer   i;
    reg [1:0] cand;             // candidate line examined this iteration
    reg [1:0] gidx;             // line actually granted (latched)
    reg       found;

    // combinational grant: first requesting line at or after `base`, wrapping
    always @(*) begin
        grant = 4'b0000;
        found = 1'b0;
        gidx  = base;
        for (i = 0; i < 4; i = i + 1) begin
            cand = base + i[1:0];        // 2-bit wrap-around
            if (!found && req[cand]) begin
                grant = 4'b0001 << cand;
                gidx  = cand;            // remember who was served
                found = 1'b1;
            end
        end
    end

    // rotate the base to just past whoever was granted
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            base <= 2'd0;
        else if (found)
            base <= gidx + 2'd1;         // rotation: next cycle starts after served line
    end
endmodule
