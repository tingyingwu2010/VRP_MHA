import tensorflow as tf
from layers import MultiHeadAttention, DotProductAttention

class DecoderCell(tf.keras.layers.Layer):
	def __init__(self, n_heads = 8, clip = 10., **kwargs):
		super().__init__(**kwargs)
		self.n_heads = n_heads
		self.clip = clip

	def build(self, input_shape):
		context_shape, nodes_shape = input_shape
		self.prep_attention_layer = MultiHeadAttention(n_heads = self.n_heads, embed_dim = nodes_shape[2])
		self.final_attention_layer = DotProductAttention(return_logits = True, clip = self.clip)
		super().build(input_shape)

	def call(self, inputs, mask = None):
		context, nodes = inputs
		query = self.prep_attention_layer([context, nodes, nodes], mask = mask)
		logits = self.final_attention_layer([query, nodes, nodes], mask = mask)
		return logits

class Sampler(tf.keras.layers.Layer):
	def __init__(self, n_samples = 1, **kwargs):
		super().__init__(**kwargs)
		self.n_samples = n_samples
		""" logits: (batch, n_classes)
			TopKSampler <-- greedy; sample ones with bigger probability
			CategoricalSampler <-- sampling; randomly sample ones based on probability
		"""

class TopKSampler(Sampler):
	def call(self, logits):
		return tf.math.top_k(logits, self.n_samples).indices

class CategoricalSampler(Sampler):
	def call(self, logits):
		return tf.random.categorical(logits, self.n_samples, dtype = tf.int32)

if __name__ == '__main__':
	batch, n_nodes, embed_dim = 5, 21, 128
	context = tf.ones((batch, 1, 2*embed_dim + 1), dtype = tf.float32)
	nodes = tf.ones((batch, n_nodes, embed_dim), dtype = tf.float32)
	mask = tf.zeros((batch, n_nodes, 1), dtype = tf.bool)
	decoder = DecoderCell()
	logits = decoder([context, nodes], mask)
	print(logits.shape)# logits: (batch, 1, n_nodes), logits denotes the value before going into softmax
	sampler = TopKSampler() 
	next_node = sampler(tf.squeeze(logits, axis = 1))
	print(next_node.shape)# next node: (batch, 1)
	
