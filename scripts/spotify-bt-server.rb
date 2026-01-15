#!/usr/bin/env ruby
# frozen_string_literal: true

#
# Spotify BT REST API Server
# Sinatra wrapper for spotify-bt-control.sh
#
# Endpoints:
#   GET  /speakers              - List paired audio devices
#   POST /connect               - Connect to device (body: {"address": "mac"})
#   POST /disconnect            - Disconnect device (body: {"address": "mac"})
#   GET  /status                - BT connection status
#   POST /spotify/play          - Play/resume Spotify
#   POST /spotify/pause         - Pause Spotify
#   GET  /spotify/status        - Spotify status
#   GET  /health                - Health check
#

require 'sinatra'
require 'json'
require 'logger'

# === Configuration ===

set :port, ENV.fetch('PORT', '8766').to_i
set :bind, ENV.fetch('BIND_HOST', '0.0.0.0')
set :server, 'webrick'
set :logging, true

# Log level from ENV
if ENV['LOG_LEVEL']
  case ENV['LOG_LEVEL'].downcase
  when 'debug'
    set :logging, Logger::DEBUG
  when 'info'
    set :logging, Logger::INFO
  when 'warn'
    set :logging, Logger::WARN
  when 'error'
    set :logging, Logger::ERROR
  end
end

SCRIPT_DIR = File.expand_path('../scripts', __dir__)
CONTROL_SCRIPT = File.join(SCRIPT_DIR, 'spotify-bt-control.sh')

# === Helpers ===

def execute_command(*args)
  cmd = [CONTROL_SCRIPT] + args
  
  stdout, stderr, status = Open3.capture3(*cmd)
  
  unless status.success?
    error_msg = stderr.empty? ? stdout : stderr
    begin
      error_json = JSON.parse(error_msg)
      halt 400, json(error_json)
    rescue JSON::ParserError
      halt 500, json(error: error_msg.strip)
    end
  end
  
  begin
    JSON.parse(stdout)
  rescue JSON::ParserError
    { success: true, output: stdout.strip }
  end
end

def json(data)
  content_type :json
  JSON.generate(data)
end

def parse_json_body
  return {} if request.body.size.zero?
  
  request.body.rewind if request.body.respond_to?(:rewind)
  body_content = request.body.read
  
  return {} if body_content.empty?
  
  JSON.parse(body_content, symbolize_names: true)
rescue JSON::ParserError => e
  halt 400, json(error: "Invalid JSON: #{e.message}")
end
# === Routes ===

before do
  # Log request
  logger.info "#{request.request_method} #{request.path_info}"
end

# Health check
get '/health' do
  json(
    status: 'ok',
    timestamp: Time.now.iso8601,
    version: '1.0.0'
  )
end

# List paired audio devices
get '/speakers' do
  result = execute_command('list')
  json(result)
end

# Connect to BT device
post '/connect' do
  body = parse_json_body
  address = body[:address]
  
  halt 400, json(error: 'Missing address parameter') unless address
  
  result = execute_command('connect', address)
  json(result)
end

# Disconnect BT device
post '/disconnect' do
  body = parse_json_body
  address = body[:address]
  
  halt 400, json(error: 'Missing address parameter') unless address
  
  result = execute_command('disconnect', address)
  json(result)
end

# BT connection status
get '/status' do
  result = execute_command('status')
  json(result)
end

# Spotify: Play/Resume
post '/spotify/play' do
  result = execute_command('spotify-play')
  json(result)
end

# Spotify: Pause
post '/spotify/pause' do
  result = execute_command('spotify-pause')
  json(result)
end

# Spotify: Status
get '/spotify/status' do
  result = execute_command('spotify-status')
  json(result)
end

# 404 handler
not_found do
  json(
    error: 'Endpoint not found',
    path: request.path_info
  )
end

# Error handler
error do
  err = env['sinatra.error']
  logger.error "Error: #{err.message}"
  logger.error err.backtrace.join("\n")
  
  json(
    error: 'Internal server error',
    message: err.message
  )
end

# === Startup ===

if __FILE__ == $PROGRAM_NAME
  # Check if control script exists
  unless File.executable?(CONTROL_SCRIPT)
    abort "Control script not found or not executable: #{CONTROL_SCRIPT}"
  end
  
  puts "Starting Spotify BT API server on #{settings.bind}:#{settings.port}"
  puts "Control script: #{CONTROL_SCRIPT}"
  puts
  
  require 'open3'
  Sinatra::Application.run!
end
