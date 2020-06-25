import tensorflow as tf
from tqdm import tqdm

from model import AttentionModel
from rollout import RolloutBaseline
from data import generate_data
from config import Config, load_pkl, pkl_parser

def REINFORCE(model, inputs, bs, baseline, t):
	with tf.GradientTape() as tape:
		L, logp = model(inputs)
		b = bs[t] if bs is not None else baseline.eval(inputs, L)
		adv = L - tf.stop_gradient(b)
		grad_target, L_mean = tf.reduce_mean(adv * logp), tf.reduce_mean(L)
	grad = tape.gradient(grad_target, model.trainable_variables)# model.trainable_variables == thita
	return grad_target, grad, L_mean
	
def train(cfg, log_path = None):
	model = AttentionModel(cfg.embed_dim, cfg.n_encode_layers, cfg.n_heads, 
						cfg.tanh_clipping, 'sampling')
	baseline = RolloutBaseline(model, cfg.task, cfg.weight_dir, cfg.n_samples, 
								cfg.embed_dim, cfg.n_customer, cfg.warmup_beta)
	optimizer = tf.keras.optimizers.Adam(learning_rate = cfg.lr)
	ave_loss = tf.keras.metrics.Mean()
	ave_L = tf.keras.metrics.Mean()
	loss_list, L_list = [], []

	for epoch in tqdm(range(cfg.epochs), desc = 'epoch'):
		dataset = generate_data(cfg.n_samples, cfg.n_customer)
		bs = baseline.eval_all(dataset)
		bs = tf.reshape(bs, (-1, cfg.batch)) if bs is not None else None # (cfg.batch_steps, cfg.batch) or None
		
		for t, inputs in tqdm(enumerate(dataset.batch(cfg.batch))):
			grad_target, grad, L_mean = REINFORCE(model, inputs, bs, baseline, t)
			optimizer.apply_gradients(zip(grad, model.trainable_variables))# update model parameter

			ave_loss.update_state(grad_target)
			ave_L.update_state(L_mean)

		baseline.epoch_callback(model, epoch)
		model.decode_type = 'sampling'
		model.save_weights('%s%s_epoch%s.h5'%(cfg.weight_dir, cfg.task, epoch), save_format = 'h5')
		loss_list.append(ave_loss.result().numpy())
		ave_loss.reset_states()
		L_list.append(ave_L.result().numpy())
		ave_L.reset_states()
		if cfg.islogger:
				if log_path is None:
					log_path = '%s%s_%s.csv'%(cfg.log_dir, cfg.task, cfg.dump_date)#cfg.log_dir = ./Csv/
					with open(log_path, 'w') as f:
						f.write('epoch,loss,average length\n')
				else:
					with open(log_path, 'a') as f:
						f.write('%d,%1.3f,%1.3f\n'%(epoch, loss_list[-1], L_list[-1]))

if __name__ == '__main__':
	cfg = load_pkl(pkl_parser().path)
	train(cfg)


	