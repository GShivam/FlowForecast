import torch
from torch.nn.modules.activation import MultiheadAttention
from flood_forecast.transformer_xl.lower_upper_config import activation_dict
from flood_forecast.transformer_xl.transformer_basic import SimplePositionalEncoding


class MultiAttnHeadSimple(torch.nn.Module):
    """A simple multi-head attention model inspired by Vaswani et al."""

    def __init__(
            self,
            number_time_series: int,
            seq_len=10,
            output_seq_len=None,
            d_model=128,
            num_heads=8,
            dropout=0.1,
            output_dim=1,
            final_layer=False):
        """

        :param number_time_series: The total number of time series present
        :type number_time_series: int
        :param seq_len: The forecast_history, defaults to 10
        :type seq_len: int, optional
        :param output_seq_len: The forecast length, defaults to None
        :type output_seq_len: [type], optional
        :param d_model: The dimensional embedding of the multi-head mech, defaults to 128
        :type d_model: int, optional
        :param num_heads: [description], defaults to 8
        :type num_heads: int, optional
        :param dropout: [description], defaults to 0.1
        :type dropout: float, optional
        :param output_dim: [description], defaults to 1
        :type output_dim: int, optional
        :param final_layer: [description], defaults to False
        :type final_layer: bool, optional
        """

        super().__init__()
        self.dense_shape = torch.nn.Linear(number_time_series, d_model)
        self.pe = SimplePositionalEncoding(d_model)
        self.multi_attn = MultiheadAttention(
            embed_dim=d_model, num_heads=num_heads, dropout=dropout)
        self.final_layer = torch.nn.Linear(d_model, output_dim)
        self.length_data = seq_len
        self.forecast_length = output_seq_len
        self.sigmoid = None
        self.output_dim = output_dim
        if self.forecast_length:
            self.last_layer = torch.nn.Linear(seq_len, output_seq_len)
        if final_layer:
            self.sigmoid = activation_dict[final_layer]()

    def forward(self, x: torch.Tensor, mask=None) -> torch.Tensor:
        """
        :param: x torch.Tensor: of shape (B, L, M)
        Where B is the batch size, L is the sequence length and M is the number of time
        :return: a tensor of dimension (B, forecast_length)
        """
        x = self.dense_shape(x)
        x = self.pe(x)
        # Permute to (L, B, M)
        x = x.permute(1, 0, 2)
        if mask is None:
            x = self.multi_attn(x, x, x)[0]
        else:
            x = self.multi_attn(x, x, x, attn_mask=self.mask)[0]
        x = self.final_layer(x)
        if self.forecast_length:
            # Switch to (B, M, L)
            x = x.permute(1, 2, 0)
            x = self.last_layer(x)
            if self.sigmoid:
                x = self.sigmoid(x)
            if self.output_dim > 1:
                return x.permute(0, 2, 1)
            return x.view(-1, self.forecast_length)
        return x.view(-1, self.length_data)
